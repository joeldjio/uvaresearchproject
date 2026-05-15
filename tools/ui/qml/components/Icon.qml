import QtQuick
import QtQuick.Shapes

/*
 * Minimal monochrome icon set rendered as vector shapes via Qt Quick.
 * Use as: Cmp.Icon { name: "home"; color: "#e2e8f0"; size: 14 }
 * Available names:
 *   home, folder, save, trash, plus, map, target, list, search,
 *   camera, gear, warning, bolt, stop, play, refresh, check, x,
 *   chevron-up, chevron-down, chevron-left, chevron-right, drone
 */
Item {
    id: root
    property string name: ""
    property color  color: "#e2e8f0"
    property real   size: 14
    property real   strokeW: 1.6
    implicitWidth:  size
    implicitHeight: size
    width:  size
    height: size

    Shape {
        id: shp
        anchors.fill: parent
        antialiasing: true
        layer.enabled: true
        layer.samples: 4

        // Each icon is normalized to a 24x24 viewBox, scaled to size.
        readonly property real s: root.size / 24

        ShapePath {
            strokeColor: root.color
            fillColor:   "transparent"
            strokeWidth: root.strokeW
            capStyle:    ShapePath.RoundCap
            joinStyle:   ShapePath.RoundJoin

            // Translate paths from a normalized 24x24 grid.
            startX: 0; startY: 0

            PathSvg {
                path: {
                    var s = shp.s
                    function P(d) {
                        // scale a 24x24 SVG path by s
                        return d.replace(/(-?\d+\.?\d*)/g, function(n){ return (parseFloat(n) * s).toFixed(2) })
                    }
                    switch (root.name) {
                    case "home":     return P("M 3 12 L 12 3 L 21 12 M 5 10 L 5 21 L 10 21 L 10 14 L 14 14 L 14 21 L 19 21 L 19 10")
                    case "folder":   return P("M 3 7 L 10 7 L 12 9 L 21 9 L 21 19 L 3 19 Z")
                    case "save":     return P("M 4 4 L 17 4 L 20 7 L 20 20 L 4 20 Z M 7 4 L 7 9 L 16 9 L 16 4 M 7 20 L 7 13 L 17 13 L 17 20")
                    case "trash":    return P("M 4 7 L 20 7 M 9 7 L 9 4 L 15 4 L 15 7 M 6 7 L 7 20 L 17 20 L 18 7 M 10 11 L 10 17 M 14 11 L 14 17")
                    case "plus":     return P("M 12 5 L 12 19 M 5 12 L 19 12")
                    case "map":      return P("M 3 6 L 9 4 L 15 6 L 21 4 L 21 18 L 15 20 L 9 18 L 3 20 Z M 9 4 L 9 18 M 15 6 L 15 20")
                    case "target":   return P("M 12 3 L 12 7 M 12 17 L 12 21 M 3 12 L 7 12 M 17 12 L 21 12 M 12 8 A 4 4 0 1 1 11.99 8 Z")
                    case "list":     return P("M 4 6 L 20 6 M 4 12 L 20 12 M 4 18 L 20 18")
                    case "search":   return P("M 11 4 A 7 7 0 1 1 10.99 4 Z M 16 16 L 21 21")
                    case "camera":   return P("M 4 8 L 8 8 L 10 5 L 14 5 L 16 8 L 20 8 L 20 19 L 4 19 Z M 12 10 A 4 4 0 1 1 11.99 10 Z")
                    case "gear":     return P("M 12 8 A 4 4 0 1 1 11.99 8 Z M 12 2 L 12 5 M 12 19 L 12 22 M 2 12 L 5 12 M 19 12 L 22 12 M 5 5 L 7 7 M 17 17 L 19 19 M 5 19 L 7 17 M 17 7 L 19 5")
                    case "warning":  return P("M 12 3 L 22 20 L 2 20 Z M 12 10 L 12 15 M 12 17 L 12 18")
                    case "bolt":     return P("M 13 2 L 4 14 L 11 14 L 9 22 L 20 9 L 13 9 Z")
                    case "stop":     return P("M 6 6 L 18 6 L 18 18 L 6 18 Z")
                    case "play":     return P("M 7 4 L 20 12 L 7 20 Z")
                    case "refresh":  return P("M 21 12 A 9 9 0 1 1 18 5 M 18 2 L 18 6 L 14 6")
                    case "check":    return P("M 4 12 L 10 18 L 20 6")
                    case "x":        return P("M 5 5 L 19 19 M 19 5 L 5 19")
                    case "chevron-up":    return P("M 5 15 L 12 8 L 19 15")
                    case "chevron-down":  return P("M 5 9 L 12 16 L 19 9")
                    case "chevron-left":  return P("M 15 5 L 8 12 L 15 19")
                    case "chevron-right": return P("M 9 5 L 16 12 L 9 19")
                    case "drone":    return P("M 12 9 A 3 3 0 1 1 11.99 9 Z M 5 5 A 2 2 0 1 1 4.99 5 Z M 19 5 A 2 2 0 1 1 18.99 5 Z M 5 19 A 2 2 0 1 1 4.99 19 Z M 19 19 A 2 2 0 1 1 18.99 19 Z M 6 6 L 10 10 M 18 6 L 14 10 M 6 18 L 10 14 M 18 18 L 14 14")
                    case "power":    return P("M 12 3 L 12 12 M 7 6 A 8 8 0 1 0 17 6")
                    case "lock":     return P("M 6 11 L 18 11 L 18 20 L 6 20 Z M 8 11 L 8 7 A 4 4 0 0 1 16 7 L 16 11")
                    case "shield":   return P("M 12 3 L 20 6 L 20 13 C 20 17 16 20 12 21 C 8 20 4 17 4 13 L 4 6 Z")
                    case "wifi":     return P("M 5 9 C 9 5 15 5 19 9 M 8 12 C 10 10 14 10 16 12 M 11 15 L 13 15")
                    case "settings": return P("M 4 6 L 20 6 M 4 12 L 20 12 M 4 18 L 20 18 M 9 6 A 2 2 0 1 1 8.99 6 Z M 15 12 A 2 2 0 1 1 14.99 12 Z M 7 18 A 2 2 0 1 1 6.99 18 Z")
                    case "flag":     return P("M 5 21 L 5 4 L 18 4 L 15 8 L 18 12 L 5 12")
                    case "broadcast":return P("M 12 12 A 2 2 0 1 1 11.99 12 Z M 8 8 C 6 10 6 14 8 16 M 16 8 C 18 10 18 14 16 16 M 5 5 C 2 8 2 16 5 19 M 19 5 C 22 8 22 16 19 19")
                    case "info":     return P("M 12 4 A 8 8 0 1 1 11.99 4 Z M 12 11 L 12 17 M 12 8 L 12 9")
                    }
                    return ""
                }
            }
        }
    }
}
