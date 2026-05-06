#!/usr/bin/env python3
"""
DroneResearch Pi Server
=======================
Lightweight MAVLink GCS + REST API for Raspberry Pi 1.

Dependencies: ONLY pymavlink + pyserial (stdlib for everything else)
RAM usage:    ~18-25 MB
CPU:          <5% on Pi 1 at idle

REST API:
    GET  /api/status       — connection status + uptime
    GET  /api/telemetry    — latest telemetry snapshot (JSON)
    GET  /api/log          — last N log lines
    POST /api/command      — send command {cmd, params}
    GET  /                 — web dashboard (inline HTML)

Usage:
    python3 pi/server.py --port /dev/ttyUSB0 --baud 57600 --http 8080
    python3 pi/server.py --port tcp:127.0.0.1:5760 --http 8080
"""
import argparse
import json
import math
import os
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# ── Try pymavlink ──────────────────────────────────────────────────────────────
try:
    from pymavlink import mavutil
    _MAV_OK = True
except ImportError:
    _MAV_OK = False
    print("[WARN] pymavlink not found — running in demo mode", file=sys.stderr)

# ── Global state (plain dict — no dataclass overhead) ─────────────────────────
_state = {
    "connected":    False,
    "autopilot":    "unknown",
    "armed":        False,
    "mode":         "UNKNOWN",
    "lat":          0.0,
    "lon":          0.0,
    "alt":          0.0,
    "alt_rel":      0.0,
    "roll":         0.0,
    "pitch":        0.0,
    "yaw":          0.0,
    "vx":           0.0,
    "vy":           0.0,
    "vz":           0.0,
    "groundspeed":  0.0,
    "airspeed":     0.0,
    "climb":        0.0,
    "battery_v":    0.0,
    "battery_pct":  -1.0,
    "gps_fix":      0,
    "satellites":   0,
    "throttle":     0.0,
    "last_hb":      0.0,
    "uptime":       0.0,
    "start_time":   time.time(),
}
_log:   deque = deque(maxlen=200)   # ring buffer, max 200 lines
_mav    = None
_lock   = threading.Lock()

_ARDUPILOT_MODES = {
    0:"STABILIZE",1:"ACRO",2:"ALT_HOLD",3:"AUTO",4:"GUIDED",
    5:"LOITER",6:"RTL",7:"CIRCLE",9:"LAND",16:"POSHOLD",
    17:"BRAKE",21:"SMART_RTL",
}
_PX4_MAIN = {1:"MANUAL",2:"ALTCTL",3:"POSCTL",4:"AUTO",6:"OFFBOARD",7:"STABILIZED"}

# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    entry = {"t": round(time.time(), 2), "l": level, "m": msg}
    _log.append(entry)
    print(f"[{level}] {msg}", file=sys.stderr)

# ── MAVLink connection ─────────────────────────────────────────────────────────
def connect(connection_string: str, baud: int = 57600):
    global _mav
    if not _MAV_OK:
        log("pymavlink not installed — demo mode", "WARN")
        _state["connected"] = True
        _inject_demo_data()
        return
    log(f"Connecting: {connection_string}")
    try:
        _mav = mavutil.mavlink_connection(
            connection_string,
            baud=baud,
            source_system=255,
            autoreconnect=True,
        )
        log("Waiting for heartbeat...")
        hb = _mav.wait_heartbeat(timeout=15)
        if hb is None:
            log("No heartbeat received", "ERROR")
            return
        _detect_autopilot(hb)
        _state["connected"] = True
        log(f"Connected. Autopilot: {_state['autopilot']}")
        _request_streams()
    except Exception as e:
        log(f"Connection error: {e}", "ERROR")
        return
    # Start receive loop in background thread
    t = threading.Thread(target=_rx_loop, daemon=True, name="mav-rx")
    t.start()

def _detect_autopilot(hb):
    ap = getattr(hb, "autopilot", 0)
    if ap == 3:
        _state["autopilot"] = "ardupilot"
    elif ap == 12:
        _state["autopilot"] = "px4"

def _request_streams():
    if not _mav:
        return
    # Low rates for Pi 1 — only what we need
    for sid, rate in [(6, 2), (10, 4), (11, 2), (2, 1)]:
        _mav.mav.request_data_stream_send(
            _mav.target_system, _mav.target_component, sid, rate, 1
        )

def _rx_loop():
    while True:
        if not _mav:
            time.sleep(1)
            continue
        try:
            msg = _mav.recv_match(blocking=True, timeout=2.0)
        except Exception as e:
            log(f"RX error: {e}", "WARN")
            time.sleep(0.5)
            continue
        if msg is None:
            continue
        _parse(msg)

def _parse(msg):
    t = msg.get_type()
    if t == "HEARTBEAT":
        armed = bool(msg.base_mode & 0x80)
        mode  = _decode_mode(msg)
        with _lock:
            _state["armed"]  = armed
            _state["mode"]   = mode
            _state["last_hb"] = time.time()
            _state["uptime"]  = round(time.time() - _state["start_time"], 1)
    elif t == "GLOBAL_POSITION_INT":
        with _lock:
            _state["lat"]     = msg.lat / 1e7
            _state["lon"]     = msg.lon / 1e7
            _state["alt"]     = msg.alt / 1000.0
            _state["alt_rel"] = msg.relative_alt / 1000.0
            _state["vx"]      = msg.vx / 100.0
            _state["vy"]      = msg.vy / 100.0
            _state["vz"]      = msg.vz / 100.0
            _state["groundspeed"] = math.hypot(msg.vx / 100.0, msg.vy / 100.0)
    elif t == "ATTITUDE":
        with _lock:
            _state["roll"]  = round(math.degrees(msg.roll), 1)
            _state["pitch"] = round(math.degrees(msg.pitch), 1)
            _state["yaw"]   = round(math.degrees(msg.yaw) % 360, 1)
    elif t == "VFR_HUD":
        with _lock:
            _state["airspeed"]    = msg.airspeed
            _state["groundspeed"] = msg.groundspeed
            _state["climb"]       = msg.climb
            _state["throttle"]    = msg.throttle
            _state["alt"]         = msg.alt
    elif t == "SYS_STATUS":
        with _lock:
            if msg.battery_remaining >= 0:
                _state["battery_pct"] = float(msg.battery_remaining)
            if msg.voltage_battery > 0:
                _state["battery_v"] = msg.voltage_battery / 1000.0
    elif t == "BATTERY_STATUS":
        with _lock:
            if msg.voltages and msg.voltages[0] != 65535:
                _state["battery_v"] = msg.voltages[0] / 1000.0
            if msg.battery_remaining >= 0:
                _state["battery_pct"] = float(msg.battery_remaining)
    elif t == "GPS_RAW_INT":
        with _lock:
            _state["gps_fix"]    = msg.fix_type
            _state["satellites"] = msg.satellites_visible
    elif t == "STATUSTEXT":
        log(f"[FC] {msg.text}", "FC")

def _decode_mode(hb) -> str:
    ap = _state.get("autopilot", "unknown")
    if ap == "ardupilot":
        return _ARDUPILOT_MODES.get(hb.custom_mode, f"MODE_{hb.custom_mode}")
    elif ap == "px4":
        main = (hb.custom_mode >> 16) & 0xFF
        return _PX4_MAIN.get(main, f"PX4_{main}")
    return f"MODE_{hb.custom_mode}"

# ── Commands ───────────────────────────────────────────────────────────────────
def send_command(cmd: str, params: dict) -> dict:
    if not _mav and _MAV_OK:
        return {"ok": False, "error": "not connected"}
    cmd = cmd.upper()
    try:
        if cmd == "ARM":
            force = params.get("force", False)
            _cmd_long(400, 1.0, 21196.0 if force else 0.0)
        elif cmd == "DISARM":
            force = params.get("force", False)
            _cmd_long(400, 0.0, 21196.0 if force else 0.0)
        elif cmd == "TAKEOFF":
            alt = float(params.get("alt", 10.0))
            _set_mode("GUIDED")
            _cmd_long(22, 0,0,0,0,0,0, alt)
        elif cmd == "LAND":
            _cmd_long(21)
        elif cmd == "RTL":
            _cmd_long(20)
        elif cmd == "MODE":
            _set_mode(params.get("mode", "LOITER"))
        elif cmd == "GOTO":
            lat = float(params["lat"])
            lon = float(params["lon"])
            alt = float(params.get("alt", _state["alt_rel"]))
            _set_mode("GUIDED")
            if _mav:
                _mav.mav.mission_item_send(
                    _mav.target_system, _mav.target_component,
                    0, 3, 16, 2, 1, 0,0,0,0, lat, lon, alt
                )
        else:
            return {"ok": False, "error": f"unknown command: {cmd}"}
        log(f"CMD: {cmd} {params}")
        return {"ok": True}
    except Exception as e:
        log(f"CMD error: {e}", "ERROR")
        return {"ok": False, "error": str(e)}

def _cmd_long(cmd, p1=0,p2=0,p3=0,p4=0,p5=0,p6=0,p7=0):
    if not _mav:
        return
    _mav.mav.command_long_send(
        _mav.target_system, _mav.target_component,
        cmd, 0, p1, p2, p3, p4, p5, p6, p7
    )

def _set_mode(mode: str):
    if not _mav:
        return
    mode_map = {v: k for k, v in _ARDUPILOT_MODES.items()}
    num = mode_map.get(mode.upper())
    if num is not None:
        _cmd_long(176, 1, num)

# ── Demo data (no drone connected) ────────────────────────────────────────────
def _inject_demo_data():
    import random
    def _tick():
        t0 = time.time()
        while True:
            time.sleep(0.5)
            with _lock:
                _state["lat"]        = 48.1374 + math.sin(time.time()*0.1)*0.0003
                _state["lon"]        = 11.5754 + math.cos(time.time()*0.1)*0.0003
                _state["alt_rel"]    = 10.0 + math.sin(time.time()*0.3)*2.0
                _state["yaw"]        = (time.time()*20) % 360
                _state["roll"]       = math.sin(time.time()*0.7)*5
                _state["pitch"]      = math.cos(time.time()*0.5)*3
                _state["groundspeed"]= 3.5
                _state["battery_pct"]= max(0, 85 - (time.time()-t0)*0.1)
                _state["battery_v"]  = 12.4
                _state["armed"]      = True
                _state["mode"]       = "LOITER"
                _state["gps_fix"]    = 3
                _state["satellites"] = 10
                _state["last_hb"]    = time.time()
                _state["uptime"]     = round(time.time() - _state["start_time"], 1)
    threading.Thread(target=_tick, daemon=True).start()
    log("Demo mode: simulated telemetry running")

# ── HTTP Server ────────────────────────────────────────────────────────────────
_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DroneResearch</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:monospace;background:#0a0e14;color:#cdd6f4;font-size:13px}
header{background:#1e2030;padding:10px 16px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #313244}
h1{font-size:15px;color:#89b4fa;letter-spacing:1px}
#dot{width:10px;height:10px;border-radius:50%;background:#f38ba8;flex-shrink:0}
#dot.ok{background:#a6e3a1}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;padding:10px}
.card{background:#1e2030;border:1px solid #313244;border-radius:6px;padding:10px}
.card label{color:#6c7086;font-size:10px;text-transform:uppercase;letter-spacing:1px}
.card .val{font-size:20px;font-weight:bold;color:#cba6f7;margin-top:2px}
.card .unit{font-size:10px;color:#6c7086}
.warn .val{color:#fab387}
.danger .val{color:#f38ba8}
.ok .val{color:#a6e3a1}
#map-wrap{padding:0 10px 10px}
#map{width:100%;height:220px;background:#1e2030;border:1px solid #313244;border-radius:6px;position:relative;overflow:hidden}
canvas{width:100%;height:100%}
#cmds{padding:0 10px 10px;display:flex;flex-wrap:wrap;gap:6px}
button{background:#313244;color:#cdd6f4;border:1px solid #45475a;border-radius:4px;padding:6px 14px;cursor:pointer;font-family:monospace;font-size:12px}
button:hover{background:#45475a}
button.red{border-color:#f38ba8;color:#f38ba8}
button.grn{border-color:#a6e3a1;color:#a6e3a1}
button.yel{border-color:#f9e2af;color:#f9e2af}
#log-wrap{padding:0 10px 10px}
#log{background:#11111b;border:1px solid #313244;border-radius:6px;height:120px;overflow-y:auto;padding:6px;font-size:11px;color:#6c7086}
.log-FC{color:#89b4fa}.log-ERROR{color:#f38ba8}.log-WARN{color:#fab387}.log-INFO{color:#a6e3a1}
#status-bar{background:#11111b;padding:4px 16px;font-size:10px;color:#585b70;border-top:1px solid #313244}
</style>
</head>
<body>
<header>
  <div id="dot"></div>
  <h1>DroneResearch &#128641;</h1>
  <span id="mode-badge" style="background:#313244;padding:2px 8px;border-radius:4px;font-size:11px">---</span>
  <span id="armed-badge" style="padding:2px 8px;border-radius:4px;font-size:11px;background:#313244">DISARMED</span>
  <span style="margin-left:auto;color:#585b70;font-size:11px" id="uptime">up 0s</span>
</header>

<div class="grid">
  <div class="card" id="c-alt"><label>Altitude</label><div class="val" id="alt">--</div><span class="unit">m</span></div>
  <div class="card" id="c-spd"><label>Groundspeed</label><div class="val" id="spd">--</div><span class="unit">m/s</span></div>
  <div class="card" id="c-bat"><label>Battery</label><div class="val" id="bat">--</div><span class="unit">%</span></div>
  <div class="card"><label>Battery V</label><div class="val" id="batv">--</div><span class="unit">V</span></div>
  <div class="card"><label>Roll</label><div class="val" id="roll">--</div><span class="unit">deg</span></div>
  <div class="card"><label>Pitch</label><div class="val" id="pitch">--</div><span class="unit">deg</span></div>
  <div class="card"><label>Heading</label><div class="val" id="yaw">--</div><span class="unit">deg</span></div>
  <div class="card" id="c-gps"><label>GPS Fix</label><div class="val" id="gps">--</div><span class="unit" id="sats"></span></div>
</div>

<div id="map-wrap">
  <canvas id="map"></canvas>
</div>

<div id="cmds">
  <button class="grn" onclick="cmd('ARM')">ARM</button>
  <button class="red" onclick="cmd('DISARM')">DISARM</button>
  <button class="yel" onclick="cmd('TAKEOFF',{alt:10})">TAKEOFF 10m</button>
  <button onclick="cmd('LAND')">LAND</button>
  <button onclick="cmd('RTL')">RTL</button>
  <button onclick="cmd('MODE',{mode:'LOITER'})">LOITER</button>
  <button onclick="cmd('MODE',{mode:'GUIDED'})">GUIDED</button>
  <button onclick="cmd('MODE',{mode:'STABILIZE'})">STABILIZE</button>
</div>

<div id="log-wrap">
  <div id="log"></div>
</div>
<div id="status-bar">DroneResearch Pi &mdash; <span id="lat-lon">---</span></div>

<script>
const trail=[];let lastLat=0,lastLon=0;
async function poll(){
  try{
    const r=await fetch('/api/telemetry');
    const d=await r.json();
    update(d);
  }catch(e){}
}
async function pollLog(){
  try{
    const r=await fetch('/api/log?n=50');
    const lines=await r.json();
    const el=document.getElementById('log');
    el.innerHTML=lines.map(l=>`<span class="log-${l.l}">[${new Date(l.t*1000).toISOString().substr(11,8)}] ${l.m}</span>`).join('<br>');
    el.scrollTop=el.scrollHeight;
  }catch(e){}
}
function update(d){
  document.getElementById('dot').className=d.connected?'ok':'';
  document.getElementById('mode-badge').textContent=d.mode||'---';
  const ab=document.getElementById('armed-badge');
  ab.textContent=d.armed?'ARMED':'DISARMED';
  ab.style.background=d.armed?'#f38ba855':'#313244';
  ab.style.color=d.armed?'#f38ba8':'#6c7086';
  document.getElementById('uptime').textContent='up '+d.uptime+'s';
  document.getElementById('alt').textContent=(d.alt_rel||0).toFixed(1);
  document.getElementById('spd').textContent=(d.groundspeed||0).toFixed(1);
  const bp=d.battery_pct;
  document.getElementById('bat').textContent=bp>=0?bp.toFixed(0):'--';
  document.getElementById('c-bat').className='card'+(bp>=0&&bp<20?' danger':bp>=0&&bp<40?' warn':'');
  document.getElementById('batv').textContent=(d.battery_v||0).toFixed(2);
  document.getElementById('roll').textContent=(d.roll||0).toFixed(1);
  document.getElementById('pitch').textContent=(d.pitch||0).toFixed(1);
  document.getElementById('yaw').textContent=(d.yaw||0).toFixed(0);
  document.getElementById('gps').textContent=d.gps_fix>=3?'3D FIX':d.gps_fix>0?'WEAK':'NO FIX';
  document.getElementById('c-gps').className='card'+(d.gps_fix>=3?' ok':d.gps_fix>0?' warn':' danger');
  document.getElementById('sats').textContent=d.satellites+' sats';
  document.getElementById('lat-lon').textContent=`${(d.lat||0).toFixed(6)}, ${(d.lon||0).toFixed(6)}`;
  drawMap(d);
}
function drawMap(d){
  const cv=document.getElementById('map');
  const ctx=cv.getContext('2d');
  cv.width=cv.offsetWidth; cv.height=cv.offsetHeight;
  const W=cv.width,H=cv.height;
  ctx.fillStyle='#11111b'; ctx.fillRect(0,0,W,H);
  // Grid
  ctx.strokeStyle='#1e2030'; ctx.lineWidth=1;
  for(let x=0;x<W;x+=40){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
  for(let y=0;y<H;y+=40){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
  if(!d.lat) return;
  if(lastLat!==d.lat||lastLon!==d.lon){
    trail.push([d.lat,d.lon]);
    if(trail.length>120) trail.shift();
    lastLat=d.lat; lastLon=d.lon;
  }
  const cx=W/2,cy=H/2;
  const scale=800000;
  function toXY(lat,lon){
    return [cx+(lon-d.lon)*scale, cy-(lat-d.lat)*scale];
  }
  // Trail
  if(trail.length>1){
    ctx.beginPath(); ctx.strokeStyle='#45475a'; ctx.lineWidth=1;
    const[tx,ty]=toXY(trail[0][0],trail[0][1]);
    ctx.moveTo(tx,ty);
    for(let i=1;i<trail.length;i++){
      const[x,y]=toXY(trail[i][0],trail[i][1]);
      ctx.lineTo(x,y);
    }
    ctx.stroke();
  }
  // Drone icon
  const yaw=Math.PI*d.yaw/180;
  ctx.save(); ctx.translate(cx,cy); ctx.rotate(yaw);
  ctx.fillStyle=d.armed?'#f38ba8':'#89b4fa';
  ctx.beginPath();
  ctx.moveTo(0,-12); ctx.lineTo(8,8); ctx.lineTo(0,4); ctx.lineTo(-8,8); ctx.closePath();
  ctx.fill();
  ctx.restore();
  // Heading line
  ctx.strokeStyle='#fab387'; ctx.lineWidth=2;
  ctx.beginPath();
  ctx.moveTo(cx,cy);
  ctx.lineTo(cx+Math.sin(yaw)*20, cy-Math.cos(yaw)*20);
  ctx.stroke();
}
async function cmd(c,p={}){
  try{
    const r=await fetch('/api/command',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({cmd:c,params:p})
    });
    const d=await r.json();
    if(!d.ok) alert('Error: '+d.error);
  }catch(e){alert('Request failed: '+e);}
}
setInterval(poll,500);
setInterval(pollLog,2000);
poll(); pollLog();
</script>
</body>
</html>
"""

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # suppress access log — saves CPU

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/":
            self._send(200, "text/html", _DASHBOARD_HTML.encode())
        elif path == "/api/telemetry":
            with _lock:
                data = dict(_state)
            self._json(data)
        elif path == "/api/status":
            self._json({
                "connected": _state["connected"],
                "uptime":    _state["uptime"],
                "autopilot": _state["autopilot"],
            })
        elif path == "/api/log":
            qs = parse_qs(parsed.query)
            n  = int(qs.get("n", [50])[0])
            self._json(list(_log)[-n:])
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        if self.path == "/api/command":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                payload = json.loads(body)
                result  = send_command(
                    payload.get("cmd", ""),
                    payload.get("params", {}),
                )
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            self._json(result)
        else:
            self._send(404, "text/plain", b"Not found")

    def _json(self, obj):
        body = json.dumps(obj, separators=(",", ":")).encode()
        self._send(200, "application/json", body)

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="DroneResearch Pi Server")
    parser.add_argument("--port",   default="tcp:127.0.0.1:5760",
                        help="MAVLink connection (e.g. /dev/ttyUSB0 or tcp:127.0.0.1:5760)")
    parser.add_argument("--baud",   type=int, default=57600)
    parser.add_argument("--http",   type=int, default=8080,   help="HTTP port")
    parser.add_argument("--demo",   action="store_true",      help="Demo mode (no drone)")
    args = parser.parse_args()

    if args.demo:
        _state["connected"] = True
        _inject_demo_data()
        log("Running in demo mode")
    else:
        t = threading.Thread(
            target=connect, args=(args.port, args.baud), daemon=True
        )
        t.start()

    host = "0.0.0.0"
    log(f"HTTP server: http://{host}:{args.http}")
    log(f"Open in browser: http://<pi-ip>:{args.http}")

    try:
        server = HTTPServer((host, args.http), _Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down.")

if __name__ == "__main__":
    main()
