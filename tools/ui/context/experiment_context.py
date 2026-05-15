"""
ExperimentContext — ScenarioRunner bridge for QML + Python Script Runner.

QML calls:
  - experiment.run(scenarioJson)           -> JSON Scenario
  - experiment.runPythonScript(code)       -> Execute Python code
  - experiment.runPythonFile(path)         -> Execute Python file

QML receives: experiment.resultReady(result), experiment.logMessage(text), scriptFinished(success)
"""
import json
import os
import sys
import threading
import io
import contextlib
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty

try:
    from droneresearch.experiment.scenario import (
        Scenario as _Scenario,
        ScenarioRunner as _ScenarioRunner,
    )
except ImportError:
    _Scenario = None
    _ScenarioRunner = None


class ScriptExecutor(threading.Thread):
    """Executes Python script in background with stdout/stderr capture.

    The script can poll ``script_should_stop()`` (injected into its globals)
    or watch ``stop_event`` to honour a cancellation request cooperatively.
    A watchdog thread enforces ``timeout_s`` and raises KeyboardInterrupt
    inside the worker thread via ``PyThreadState_SetAsyncExc`` as a last
    resort — this is best-effort and may not interrupt C-level blocking calls.
    """

    def __init__(self, code, globals_dict, on_log, on_done, timeout_s: float = 0.0):
        super().__init__(daemon=True)
        self.code = code
        self.globals_dict = globals_dict
        self.on_log = on_log
        self.on_done = on_done
        self.timeout_s = float(timeout_s) if timeout_s and timeout_s > 0 else 0.0
        self._stop_event = threading.Event()
        self._watchdog: "threading.Timer | None" = None
        
    def run(self):
        """Execute script with captured output."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Custom stdout that both captures and emits
        class TeeIO:
            def __init__(self, real_stream, callback):
                self.real = real_stream
                self.callback = callback
                self.line_buffer = ""
                
            def write(self, data):
                self.real.write(data)
                self.line_buffer += data
                if '\n' in self.line_buffer:
                    lines = self.line_buffer.split('\n')
                    for line in lines[:-1]:
                        if line:
                            self.callback(line)
                    self.line_buffer = lines[-1]
                    
            def flush(self):
                self.real.flush()
                if self.line_buffer:
                    self.callback(self.line_buffer)
                    self.line_buffer = ""
        
        try:
            # Redirect stdout/stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = TeeIO(stdout_capture, self.on_log)
            sys.stderr = TeeIO(stderr_capture, self.on_log)
            
            # Execute in isolated namespace with droneresearch available
            namespace = {
                '__name__': '__main__',
                '__file__': '<experiment_script>',
                'exit': lambda *args: None,  # Prevent script exit
                'quit': lambda *args: None,
            }
            namespace.update(self.globals_dict)

            # Cooperative-stop hooks for the script
            namespace['stop_event'] = self._stop_event
            namespace['script_should_stop'] = self._stop_event.is_set

            # Add droneresearch to namespace
            try:
                import droneresearch
                namespace['droneresearch'] = droneresearch
                namespace['Swarm'] = droneresearch.Swarm
            except ImportError:
                pass

            # Arm watchdog (optional)
            if self.timeout_s > 0:
                def _on_timeout():
                    self.on_log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"WATCHDOG: timeout after {self.timeout_s:.0f}s — requesting stop"
                    )
                    self.request_stop()
                self._watchdog = threading.Timer(self.timeout_s, _on_timeout)
                self._watchdog.daemon = True
                self._watchdog.start()

            self.on_log(f"[{datetime.now().strftime('%H:%M:%S')}] Script started")
            exec(self.code, namespace)
            self.on_log(f"[{datetime.now().strftime('%H:%M:%S')}] Script completed")
            self.on_done(True, "Script executed successfully")

        except KeyboardInterrupt:
            self.on_log(f"[{datetime.now().strftime('%H:%M:%S')}] Script interrupted")
            self.on_done(False, "interrupted")
            
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}\n{traceback.format_exc()}"
            self.on_log(error_msg)
            self.on_done(False, str(e))
            
        finally:
            if self._watchdog is not None:
                self._watchdog.cancel()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def request_stop(self) -> None:
        """Cooperative stop — sets event; script must poll it.

        Best-effort hard interrupt via PyThreadState_SetAsyncExc is *not*
        triggered automatically here because it is unsafe in some contexts.
        Use :meth:`force_stop` if you really need to break a stuck script.
        """
        self._stop_event.set()

    def force_stop(self) -> bool:
        """Asynchronously raise KeyboardInterrupt in the worker thread.

        Returns True if the exception was set successfully. This will not
        interrupt code stuck in C-level blocking calls.
        """
        import ctypes
        if not self.is_alive():
            return False
        tid = self.ident
        if tid is None:
            return False
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(tid), ctypes.py_object(KeyboardInterrupt)
        )
        if res == 0:
            return False
        if res > 1:
            # Undo, something went wrong
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(tid), None)
            return False
        return True


class ExperimentContext(QObject):
    """QML-exposed experiment runner supporting both JSON scenarios and Python scripts."""

    # Signals
    resultReady   = pyqtSignal("QVariant", arguments=["result"])
    logMessage    = pyqtSignal(str,        arguments=["text"])
    busyChanged   = pyqtSignal()
    scriptFinished = pyqtSignal(bool, str,  arguments=["success", "message"])
    progressChanged = pyqtSignal(int,       arguments=["percent"])
    
    finished         = pyqtSignal()

    # Script execution signals
    scriptLogMessage = pyqtSignal(str,     arguments=["text"])
    scriptLineNumber = pyqtSignal(int,     arguments=["line"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self._progress = 0
        self._current_executor = None
        self._scripts_dir = Path("experiments/uploads")
        self._scripts_dir.mkdir(parents=True, exist_ok=True)
        # 0 = no timeout. UI can override via setScriptTimeout().
        self._script_timeout_s: float = 0.0
        
    # ── Properties ─────────────────────────────────────────────────────────
    
    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy
        
    @pyqtProperty(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress
        
    # ── JSON Scenario Execution ────────────────────────────────────────────

    @pyqtSlot(str, bool)
    def run(self, scenario_json: str, use_sitl: bool = True) -> None:
        """Run a JSON-defined scenario experiment."""
        if _Scenario is None:
            self.logMessage.emit("[experiment] droneresearch SDK not installed.")
            return
        if self._busy:
            return
        try:
            scenario_dict = json.loads(scenario_json)
        except json.JSONDecodeError as exc:
            self.logMessage.emit(f"[experiment] Invalid JSON: {exc}")
            return

        self._set_busy(True)

        def _run():
            try:
                scenario = _Scenario(**scenario_dict)
                runner = _ScenarioRunner(
                    scenario,
                    results_dir="results",
                    on_result=lambda r: self.resultReady.emit(r.to_dict()),
                    use_sitl=use_sitl,
                )
                self.logMessage.emit(f"[experiment] Starting: {scenario.name}")
                runner.run()
                self.logMessage.emit(f"[experiment] Done. {len(runner.results)} run(s).")
            except Exception as exc:
                self.logMessage.emit(f"[experiment] ERROR: {exc}")
            finally:
                self._set_busy(False)
                self.finished.emit()

        threading.Thread(target=_run, daemon=True).start()

    # ── Python Script Execution ───────────────────────────────────────────
    
    @pyqtSlot(str, "QVariant")
    def runPythonScript(self, code: str, globals_dict=None) -> None:
        """Execute Python code string with live log output."""
        if self._busy:
            self.scriptLogMessage.emit("[ERROR] Another experiment is running")
            return

        self._set_busy(True)

        # Convert QVariant dict to Python dict if needed
        if globals_dict is None:
            globals_dict = {}
        elif hasattr(globals_dict, 'toVariant'):
            globals_dict = globals_dict.toVariant()

        def on_log(line):
            self.scriptLogMessage.emit(line)

        def on_done(success, message):
            self._set_busy(False)
            self.scriptFinished.emit(success, message)

        self._current_executor = ScriptExecutor(
            code, globals_dict, on_log, on_done, timeout_s=self._script_timeout_s
        )
        self._current_executor.start()
        
    @pyqtSlot(str)
    def runPythonFile(self, file_path: str) -> None:
        """Execute a Python file (.py) with live log output."""
        try:
            # Clean file path
            if file_path.startswith("file:///"):
                file_path = file_path[8:]
            elif file_path.startswith("file://"):
                file_path = file_path[7:]
                
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                
            filename = os.path.basename(file_path)
            self.scriptLogMessage.emit(f"[INFO] Loading script: {filename}")
            
            # Provide __file__ in globals
            self.runPythonScript(code, {'__file__': file_path})
            
        except Exception as e:
            self.scriptLogMessage.emit(f"[ERROR] Failed to load file: {e}")
            self.scriptFinished.emit(False, str(e))
            
    @pyqtSlot(str, str)
    def saveAndRunScript(self, filename: str, code: str) -> None:
        """Save script to experiments/uploads/ and then execute it."""
        try:
            filepath = self._scripts_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            self.scriptLogMessage.emit(f"[INFO] Script saved to: {filepath}")
            self.runPythonFile(str(filepath))
        except Exception as e:
            self.scriptLogMessage.emit(f"[ERROR] Failed to save script: {e}")
            self.scriptFinished.emit(False, str(e))
            
    @pyqtSlot()
    def stopScript(self) -> None:
        """Cooperatively request the running script to stop."""
        if self._current_executor and self._current_executor.is_alive():
            self._current_executor.request_stop()
            self.scriptLogMessage.emit(
                "[WARN] Stop requested — script must poll script_should_stop() / stop_event"
            )
        else:
            self.scriptLogMessage.emit("[INFO] No script currently running")

    @pyqtSlot()
    def forceStopScript(self) -> None:
        """Hard-interrupt the running script (best effort, unsafe)."""
        if self._current_executor and self._current_executor.is_alive():
            ok = self._current_executor.force_stop()
            self.scriptLogMessage.emit(
                f"[WARN] Force-stop {'sent' if ok else 'failed'} — may not interrupt C-level blocking calls"
            )
        else:
            self.scriptLogMessage.emit("[INFO] No script currently running")

    @pyqtSlot(float)
    def setScriptTimeout(self, seconds: float) -> None:
        """Set per-script execution timeout in seconds (0 disables)."""
        self._script_timeout_s = max(0.0, float(seconds))
            
    @pyqtSlot(result="QVariant")
    def listUploadedScripts(self) -> list:
        """Return list of uploaded script filenames."""
        try:
            return [f.name for f in self._scripts_dir.glob("*.py")]
        except Exception:
            return []
            
    @pyqtSlot(str)
    def deleteScript(self, filename: str) -> None:
        """Delete an uploaded script."""
        try:
            filepath = self._scripts_dir / filename
            if filepath.exists():
                filepath.unlink()
                self.scriptLogMessage.emit(f"[INFO] Deleted: {filename}")
        except Exception as e:
            self.scriptLogMessage.emit(f"[ERROR] Failed to delete: {e}")
            
    @pyqtSlot(str, result=str)
    def readScript(self, filename: str) -> str:
        """Read an uploaded script's content."""
        try:
            filepath = self._scripts_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            return f"# Error reading file: {e}"

    # ── Helpers ───────────────────────────────────────────────────────────
    
    def _set_busy(self, busy: bool):
        self._busy = busy
        self.busyChanged.emit()
        if not busy:
            self._progress = 0
            self.progressChanged.emit(0)
