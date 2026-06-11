import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Formation Preview Component
// Shows 2D visualization of swarm formation before launch
Rectangle {
    id: root
    clip: true  // Prevent content from overflowing
    
    // Properties
    property string formationType: "v"
    property int droneCount: 4
    property real spacing: 10.0
    
    // Minimum drone count per formation type (only 4 types supported)
    // Count = followers only (leader not included)
    function getMinDroneCount(type) {
        const minimums = {
            "line": 2,     // 2 followers + 1 leader = 3 total
            "v": 2,        // 2 followers + 1 leader = 3 total
            "circle": 4,   // 4 followers + 1 leader = 5 total
            "grid": 4      // 4 followers + 1 leader = 5 total
        }
        return minimums[type] || 2
    }
    
    // Effective drone count (respects minimum, uses actual connected count)
    property int effectiveDroneCount: Math.max(droneCount, getMinDroneCount(formationType))
    property color leaderColor: "#4ade80"  // Green
    property color followerColor: "#60a5fa"  // Blue
    property color gridColor: "#334155"
    property color backgroundColor: "#0f172a"
    
    // Signals
    signal formationChanged(string type, int count, real spacing)
    
    // Watch for property changes and update canvas
    onFormationTypeChanged: canvas.updateFormation()
    onDroneCountChanged: canvas.updateFormation()
    onSpacingChanged: canvas.updateFormation()
    
    color: backgroundColor
    radius: 8
    border.color: "#1e293b"
    border.width: 1
    
    // Main layout
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        
        // Title
        Text {
            text: "FORMATION PREVIEW"
            color: "#64748b"
            font.pixelSize: 9
            font.weight: Font.Bold
            font.letterSpacing: 1
            Layout.alignment: Qt.AlignHCenter
        }
        
        // Canvas for drawing formation
        Canvas {
            id: canvas
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 120
            Layout.maximumHeight: 140
            Layout.preferredHeight: 130
            
            property var offsets: []
            property real scale: 1.0
            property real centerX: width / 2
            property real centerY: height / 2
            
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                
                // Draw grid
                drawGrid(ctx)
                
                // Draw compass
                drawCompass(ctx)
                
                // Calculate scale to fit all drones
                calculateScale()
                
                // Draw formation
                drawFormation(ctx)
            }
            
            function calculateScale() {
                if (offsets.length === 0) {
                    scale = 15.0  // Increased default zoom
                    return
                }
                
                // Find max distance from center
                var maxDist = spacing
                for (var i = 0; i < offsets.length; i++) {
                    var north = offsets[i].north
                    var east = offsets[i].east
                    var dist = Math.sqrt(north * north + east * east)
                    maxDist = Math.max(maxDist, dist)
                }
                
                // Scale to fit in canvas with smaller margin for more zoom
                var margin = 20  // Reduced from 40 to 20
                var availableSize = Math.min(width, height) - 2 * margin
                scale = availableSize / (2 * maxDist + spacing)
                
                // Apply zoom factor to make formation more visible
                scale *= 1.5  // 50% zoom increase
            }
            
            function drawGrid(ctx) {
                ctx.strokeStyle = gridColor
                ctx.lineWidth = 1
                ctx.setLineDash([2, 2])
                
                // Vertical center line
                ctx.beginPath()
                ctx.moveTo(centerX, 0)
                ctx.lineTo(centerX, height)
                ctx.stroke()
                
                // Horizontal center line
                ctx.beginPath()
                ctx.moveTo(0, centerY)
                ctx.lineTo(width, centerY)
                ctx.stroke()
                
                ctx.setLineDash([])
            }
            
            function drawCompass(ctx) {
                // North arrow
                var arrowSize = 20
                var arrowX = width - 30
                var arrowY = 30
                
                ctx.fillStyle = "#64748b"
                ctx.font = "12px sans-serif"
                ctx.textAlign = "center"
                ctx.fillText("N", arrowX, arrowY - arrowSize - 5)
                
                // Arrow
                ctx.strokeStyle = "#64748b"
                ctx.fillStyle = "#64748b"
                ctx.lineWidth = 2
                ctx.beginPath()
                ctx.moveTo(arrowX, arrowY)
                ctx.lineTo(arrowX, arrowY - arrowSize)
                ctx.stroke()
                
                // Arrow head
                ctx.beginPath()
                ctx.moveTo(arrowX, arrowY - arrowSize)
                ctx.lineTo(arrowX - 5, arrowY - arrowSize + 8)
                ctx.lineTo(arrowX + 5, arrowY - arrowSize + 8)
                ctx.closePath()
                ctx.fill()
            }
            
            function drawFormation(ctx) {
                // Draw leader at center
                drawDrone(ctx, centerX, centerY, leaderColor, "L", true)
                
                // Draw followers
                for (var i = 0; i < offsets.length; i++) {
                    var north = offsets[i].north
                    var east = offsets[i].east
                    
                    // Convert NED to screen coordinates
                    // North = -Y (up), East = +X (right)
                    var x = centerX + east * scale
                    var y = centerY - north * scale
                    
                    drawDrone(ctx, x, y, followerColor, "D" + (i + 2), false)
                }
                
                // Draw scale indicator
                drawScale(ctx)
            }
            
            function drawDrone(ctx, x, y, color, label, isLeader) {
                var radius = isLeader ? 6 : 5
                
                // Draw circle
                ctx.fillStyle = color
                ctx.beginPath()
                ctx.arc(x, y, radius, 0, 2 * Math.PI)
                ctx.fill()
                
                // Draw border
                ctx.strokeStyle = "#ffffff"
                ctx.lineWidth = 1
                ctx.stroke()
                
                // Draw label (smaller font for compact view)
                ctx.fillStyle = "#ffffff"
                ctx.font = isLeader ? "bold 7px sans-serif" : "6px sans-serif"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText(label, x, y)
            }
            
            function drawScale(ctx) {
                var scaleLength = 50  // pixels
                var scaleMeters = scaleLength / scale
                
                // Round to nice number
                var niceMeters = Math.pow(10, Math.floor(Math.log10(scaleMeters)))
                if (scaleMeters / niceMeters > 5) niceMeters *= 5
                else if (scaleMeters / niceMeters > 2) niceMeters *= 2
                
                var niceLength = niceMeters * scale
                
                var x = 20
                var y = height - 20
                
                // Draw scale bar
                ctx.strokeStyle = "#64748b"
                ctx.lineWidth = 2
                ctx.beginPath()
                ctx.moveTo(x, y)
                ctx.lineTo(x + niceLength, y)
                ctx.stroke()
                
                // Draw ticks
                ctx.beginPath()
                ctx.moveTo(x, y - 5)
                ctx.lineTo(x, y + 5)
                ctx.moveTo(x + niceLength, y - 5)
                ctx.lineTo(x + niceLength, y + 5)
                ctx.stroke()
                
                // Draw label
                ctx.fillStyle = "#64748b"
                ctx.font = "10px sans-serif"
                ctx.textAlign = "center"
                ctx.fillText(niceMeters.toFixed(0) + "m", x + niceLength / 2, y - 12)
            }
            
            function updateFormation() {
                if (typeof swarm === "undefined" || !swarm) {
                    offsets = []
                    requestPaint()
                    return
                }
                
                // Get offsets from backend using effective count (respects minimum)
                offsets = swarm.getFormationOffsets(formationType, effectiveDroneCount, spacing)
                requestPaint()
            }
            
            Component.onCompleted: updateFormation()
        }
        
        // Formation info (compact - no controls, bound from parent)
        Text {
            text: formationType.toUpperCase() + " · " + (effectiveDroneCount + 1) + " drones · " + spacing.toFixed(1) + "m"
            color: "#64748b"
            font.pixelSize: 9
            Layout.alignment: Qt.AlignHCenter
        }
    }
    
    // Public functions
    function setFormation(type, count, space) {
        formationType = type
        droneCount = count
        spacing = space
        canvas.updateFormation()
    }
    
    function refresh() {
        canvas.updateFormation()
    }
}
