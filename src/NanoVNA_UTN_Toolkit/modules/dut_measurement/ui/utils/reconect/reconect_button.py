from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import shiboken6

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox

_reset_sliders_after_reconnect = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.sliders_reset", "_reset_sliders_after_reconnect")

run_sweep, update_reconnect_button_state = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh", "run_sweep", "update_reconnect_button_state")


class _ScanWorker(QObject):
    """Minimal device-scan worker for in-module reconnect."""
    found = Signal(object)
    error = Signal(str)
    finished = Signal()

    def scan(self):
        try:
            from NanoVNA_UTN_Toolkit.Hardware.Hardware import get_interfaces, get_VNA
            interfaces = get_interfaces()
            if not interfaces:
                self.error.emit("No NanoVNA device detected on any port.")
                return
            for iface in interfaces:
                try:
                    vna = get_VNA(iface)
                    if vna:
                        self.found.emit(vna)
                        return
                except Exception:
                    continue
            self.error.emit("Could not connect to any detected device.")
        except Exception as exc:
            self.error.emit(f"Scan error: {exc}")
        finally:
            self.finished.emit()


def _start_scan(self):
    """Run a background device scan; update self.vna_device on success."""
    self.reconnect_button.setEnabled(False)
    self.reconnect_button.setText("Scanning...")
    self.reconnect_button.setStyleSheet("")
    self.sweep_button.setEnabled(False)

    thread = QThread()
    worker = _ScanWorker()
    worker.moveToThread(thread)

    # Keep references so Qt doesn't garbage-collect them mid-flight
    self._reconn_thread = thread
    self._reconn_worker = worker

    def on_found(vna):
        logging.info("[reconnect_device] Scan found device: %s", type(vna).__name__)
        self.vna_device = vna
        _reset_sliders_after_reconnect(self)
        if shiboken6.isValid(self.sweep_button):
            self.sweep_button.setEnabled(True)

    def on_error(msg):
        logging.warning("[reconnect_device] Scan failed: %s", msg)
        QMessageBox.critical(self, "Connection Failed", msg)

    def on_done():
        update_reconnect_button_state(self)
        thread.quit()

    worker.found.connect(on_found)
    worker.error.connect(on_error)
    worker.finished.connect(on_done)
    thread.started.connect(worker.scan)
    thread.finished.connect(thread.deleteLater)
    thread.start()


def reconnect_device(self):
    """Reconnect to the VNA device."""
    logging.info("[graphics_window.reconnect_device] Manual reconnection requested")

    # No device object → full scan
    if not self.vna_device:
        logging.info("[reconnect_device] No device reference, starting scan")
        _start_scan(self)
        return

    # Device object exists → try serial reconnect first
    self.reconnect_button.setEnabled(False)
    self.reconnect_button.setText("Connecting...")
    self.reconnect_button.setStyleSheet("")
    if hasattr(self.reconnect_button, 'style'):
        self.reconnect_button.style().unpolish(self.reconnect_button)
        self.reconnect_button.style().polish(self.reconnect_button)
        self.reconnect_button.update()
    self.sweep_button.setEnabled(False)

    serial_ok = False
    try:
        device_type = type(self.vna_device).__name__
        logging.info("[reconnect_device] Attempting serial reconnect for %s", device_type)
        if self.vna_device.connected():
            self.vna_device.disconnect()
        self.vna_device.connect()
        serial_ok = self.vna_device.connected()
    except Exception as exc:
        logging.warning("[reconnect_device] Serial reconnect exception: %s", exc)

    if serial_ok:
        logging.info("[reconnect_device] Serial reconnect succeeded")
        _reset_sliders_after_reconnect(self)
        update_reconnect_button_state(self)
        if shiboken6.isValid(self.sweep_button):
            self.sweep_button.setEnabled(True)
    else:
        # Serial reconnect failed → fall back to full port scan
        logging.warning("[reconnect_device] Serial reconnect failed, falling back to scan")
        _start_scan(self)