# ROS2 Bag Playback Controls

## Overview

The Flight Log panel now includes integrated ROS2 bag playback controls, allowing users to replay recorded flight data directly from the UI with video-player-like controls.

## Features

### 1. Dual File Format Support
- **CSV Logs**: Traditional CSV flight logs (existing functionality)
- **ROS2 Bags**: MCAP and DB3 bag files with full playback control

### 2. Playback Controls
- **Play/Pause/Stop**: Standard media controls
- **Timeline Slider**: Seek to any point in the recording
- **Playback Speed**: Adjust from 0.1x to 10.0x (±0.5x increments)
- **Time Display**: Current position and total duration (MM:SS format)
- **State Indicator**: Visual feedback (Playing/Paused/Stopped)

### 3. UI Layout
- **Top Bar**: Two buttons (OPEN CSV, OPEN BAG) + filename display
- **Playback Section**: 120px height, always visible
- **CSV Charts**: Reduced to 400px height (from 600px) to make room
- **Stats Strip**: Positioned below playback controls

## Architecture

### Backend: `BagPlaybackContext`
Location: `tools/ui/context/bag_playback_context.py`

**Responsibilities**:
- Manage `ros2 bag play` subprocess
- Parse bag metadata (duration, topics)
- Monitor playback progress
- Handle seek operations (restart with `--start-offset`)

**Key Methods**:
- `loadBag(path)`: Load bag file and extract metadata
- `play()`: Start playback subprocess
- `pause()`: Pause playback (stops subprocess, ros2 bag play doesn't support pause)
- `stop()`: Stop playback and cleanup
- `seek(position)`: Restart playback from position (0.0-1.0)

**Properties**:
- `state`: "stopped" | "playing" | "paused"
- `progress`: 0.0 to 1.0
- `duration`: Total duration in seconds
- `playbackRate`: Playback speed multiplier (0.1-10.0)

**Signals**:
- `stateChanged(str)`: Playback state changed
- `progressChanged(float)`: Progress updated (10Hz)
- `durationChanged(float)`: Duration discovered
- `playbackRateChanged(float)`: Speed changed
- `errorOccurred(str)`: Error during playback

### Frontend: `FlightLogPanel.qml`
Location: `tools/ui/qml/panels/FlightLogPanel.qml`

**Changes**:
1. Added `bagFileDlg` FileDialog for .mcap/.db3 files
2. Added `bagPlaybackSection` Rectangle (120px height)
3. Added `formatTime(seconds)` helper function
4. Modified `topBar` to include both CSV and BAG buttons
5. Reduced chart height from 600px to 400px
6. Repositioned `statsRow` below playback section

**UI Components**:
- Title + State badge (color-coded: green=playing, orange=paused, gray=stopped)
- Timeline slider with progress bar
- Time labels (current / total)
- Control buttons (Play/Pause/Stop)
- Speed controls (display + increment/decrement buttons)

## Usage

### Opening a Bag File
1. Click **"🎬 OPEN BAG"** button
2. Select `.mcap` or `.db3` file
3. Bag metadata loads automatically (duration, topics)
4. Playback controls become active

### Playback Control
- **Play**: Click "▶ PLAY" to start playback
- **Pause**: Click "⏸ PAUSE" to pause (actually stops, ros2 limitation)
- **Stop**: Click "⏹ STOP" to stop and reset to beginning
- **Seek**: Drag timeline slider to jump to specific time
- **Speed**: Click "−" or "+" to adjust playback rate

### Playback Speed
- Default: 1.0x (real-time)
- Range: 0.1x to 10.0x
- Increment: ±0.5x per click
- Display: "Speed: 2.5x" format

## Technical Details

### ROS2 Bag Play Integration
The backend uses `subprocess.Popen` to run:
```bash
ros2 bag play <path> --rate <rate> --clock [--start-offset <seconds>]
```

**Flags**:
- `--rate`: Playback speed multiplier
- `--clock`: Publish `/clock` topic for simulation time
- `--start-offset`: Start from specific time (used for seeking)

### Progress Monitoring
A background thread monitors playback:
- Polls process status every 100ms
- Calculates progress: `elapsed_time * rate / duration`
- Emits `progressChanged` signal for UI updates
- Stops when process exits or `_stop_monitoring` flag set

### Seek Implementation
Since `ros2 bag play` doesn't support runtime seeking:
1. Stop current playback
2. Calculate time offset: `position * duration`
3. Restart with `--start-offset <offset>`
4. Update progress to match position

### Limitations
- **No True Pause**: ros2 bag play doesn't support pause, so "pause" actually stops
- **Seek Restarts**: Seeking requires restarting the subprocess
- **No Frame-by-Frame**: Can't step through individual messages
- **No Reverse**: Only forward playback supported

## Service Locator Integration

The `BagPlaybackContext` is registered in `tools/ui/service_locator.py`:

```python
def _bag_playback():
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    return BagPlaybackContext()

loc.register_factory("bagPlayback", _bag_playback)
```

**Signal Wiring**:
```python
bag_playback.errorOccurred.connect(
    lambda msg: swarm.logMessage.emit("ERROR", f"[BAG] {msg}")
)
```

## Testing

Location: `tests/test_bag_playback_context.py`

**Test Coverage**:
- Initial state verification
- Playback rate bounds checking
- Bag info extraction (mocked subprocess)
- Play/stop lifecycle
- Seek with offset calculation

**Run Tests**:
```bash
pytest tests/test_bag_playback_context.py -v
```

## Future Enhancements

### Potential Improvements
1. **Map Synchronization**: Display drone position on map during playback
2. **Topic Filtering**: Select which topics to replay
3. **Message Inspector**: View individual messages at current time
4. **Playback Markers**: Add bookmarks/annotations to timeline
5. **Multi-Bag Support**: Play multiple bags simultaneously
6. **Export Clips**: Extract time ranges to new bag files
7. **Frame-by-Frame**: Step through messages one at a time (requires custom player)

### Known Issues
- QML warning about `playbackRate` binding (cosmetic, doesn't affect functionality)
- Pause button stops playback (ros2 bag play limitation)
- Seek causes brief interruption (subprocess restart)

## Related Files

**Backend**:
- `tools/ui/context/bag_playback_context.py` (268 lines)
- `tools/ui/service_locator.py` (modified)

**Frontend**:
- `tools/ui/qml/panels/FlightLogPanel.qml` (modified)

**Tests**:
- `tests/test_bag_playback_context.py` (123 lines)

**Documentation**:
- `docs/ui/bag-playback-controls.md` (this file)

## Changelog

### v0.4.0 (2026-06-09)
- ✅ Added `BagPlaybackContext` backend
- ✅ Integrated playback controls into FlightLogPanel
- ✅ Reduced CSV chart height (600px → 400px)
- ✅ Added dual file format support (CSV + Bag)
- ✅ Implemented timeline slider with seek
- ✅ Added playback speed controls (0.1x-10.0x)
- ✅ Created comprehensive test suite
- ✅ Documented architecture and usage