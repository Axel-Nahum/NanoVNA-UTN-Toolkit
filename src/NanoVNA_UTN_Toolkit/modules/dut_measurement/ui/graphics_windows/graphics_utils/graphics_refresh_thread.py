from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QMessageBox, QApplication
import numpy as np
import logging
import skrf as rf
from pathlib import Path

from NanoVNA_UTN_Toolkit.utils import safe_import

# ---------------- imports externos ---------------- #

update_plots_with_new_data = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.graphics_update",
    "update_plots_with_new_data"
)

_reset_markers_after_sweep = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.cursors_reset",
    "_reset_markers_after_sweep"
)

_reset_sliders_before_sweep = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.sliders_reset",
    "_reset_sliders_before_sweep"
)

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils",
    "get_settings"
)

get_calibration_path = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils",
    "get_calibration_path"
)

from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.methods import Methods
from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.kits import KitsCalibrator


# =========================================================
# WORKER (THREAD)
# =========================================================

class SweepWorker(QObject):

    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, vna_device, start_freq, stop_freq, segments):
        super().__init__()

        self.vna_device = vna_device
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.segments = segments

    def run(self):

        try:
            self.progress.emit(10)

            self.vna_device.datapoints = self.segments
            self.vna_device.resetSweep(self.start_freq, self.stop_freq)

            self.progress.emit(40)

            freqs = np.array(self.vna_device.read_frequencies())
            s11 = np.array(self.vna_device.readValues("data 0"))

            self.progress.emit(70)

            s21 = np.array(self.vna_device.readValues("data 1"))

            self.progress.emit(100)

            self.finished.emit({
                "freqs": freqs,
                "s11": s11,
                "s21": s21
            })

        except Exception as e:
            self.error.emit(str(e))


# =========================================================
# MAIN THREAD FUNCTIONS
# =========================================================

def run_sweep(self):

    logging.info("[run_sweep] starting sweep")

    if not self.vna_device:
        QMessageBox.warning(self, "Error", "No VNA device connected")
        return

    if not self.vna_device.connected():
        try:
            self.vna_device.connect()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            return

    _reset_sliders_before_sweep(self)

    self.sweep_button.setEnabled(False)
    self.sweep_progress_bar.setVisible(True)
    self.sweep_progress_bar.setValue(0)

    self.reconnect_button.setEnabled(False)

    # ---------------- THREAD SETUP ---------------- #

    self.thread = QThread()
    self.worker = SweepWorker(
        self.vna_device,
        self.start_freq_hz,
        self.stop_freq_hz,
        self.segments
    )

    self.worker.moveToThread(self.thread)

    self.thread.started.connect(self.worker.run)

    self.worker.progress.connect(self.sweep_progress_bar.setValue)
    self.worker.finished.connect(self.on_sweep_finished)
    self.worker.error.connect(self.on_sweep_error)

    self.worker.finished.connect(self.thread.quit)
    self.worker.finished.connect(self.worker.deleteLater)
    self.thread.finished.connect(self.thread.deleteLater)

    self.thread.start()


# =========================================================
# FINISHED CALLBACK (AQUÍ VA TODO LO DEL "VIEJO")
# =========================================================

def on_sweep_finished(self, result):

    logging.info("[on_sweep_finished] processing data")

    freqs = np.array(result["freqs"])
    s11_med = np.array(result["s11"])
    s21_med = np.array(result["s21"])

    # -------------------------------------------------
    # CALIBRATION (lo del código viejo pero limpio)
    # -------------------------------------------------

    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    calibration_method = settings.value("Calibration/Method", "---")
    kit_name = settings.value("Calibration/Name", "---")

    if "_" in kit_name:
        kit_name = kit_name.rsplit("_", 1)[0]

    cal_dir = get_calibration_path(
        "modules/dut_measurement/calibration/osm_results",
        "modules/dut_measurement/calibration/osm_results",
        Path(__file__).resolve()
    )

    methods = Methods(cal_dir)

    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
    is_import_dut = settings.value("Calibration/isImportDut", False, type=bool)

    s11 = s11_med
    s21 = s21_med

    if not kits_ok and not no_calibration and not is_import_dut:

        if calibration_method == "OSM (Open - Short - Match)":
            s11 = methods.osm_calibrate_s11(s11_med)

        elif calibration_method == "Normalization":
            cal_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            methods = Methods(cal_dir)
            s21 = methods.normalization_calibrate_s21(s21_med)

        elif calibration_method == "1-Port+N":
            s11 = methods.osm_calibrate_s11(s11_med)

            cal_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            methods = Methods(cal_dir)
            s21 = methods.normalization_calibrate_s21(s21_med)

        elif calibration_method == "Enhanced-Response":

            osm_dir = get_calibration_path(
                "modules/dut_measurement/calibration/osm_results",
                "modules/dut_measurement/calibration/osm_results",
                Path(__file__).resolve()
            )

            thru_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )

            s11, s21 = methods.enhanced_response_calibrate(
                s11_med, s21_med, osm_dir, thru_dir
            )

    elif kits_ok:

        selected_kit_dir = get_calibration_path(
            "modules/dut_measurement/calibration/Kits",
            "modules/dut_measurement/calibration/Kits",
            Path(__file__).resolve()
        )

        kits_calibrator = KitsCalibrator(selected_kit_dir)

        s11, s21 = kits_calibrator.kits_selected(
            calibration_method,
            kit_name,
            s11_med,
            s21_med
        )

    elif is_import_dut:

        settings.setValue("Calibration/DUT", True)

        data_dut = rf.Network(self.dut)

        freqs = data_dut.f
        s11 = data_dut.s[:, 0, 0]
        s21 = data_dut.s[:, 1, 0]

    # -------------------------------------------------
    # STORE DATA
    # -------------------------------------------------

    self.freqs = freqs
    self.s11 = s11
    self.s21 = s21

    # -------------------------------------------------
    # UPDATE UI
    # -------------------------------------------------

    update_plots_with_new_data(self, skip_reset=True)

    _reset_markers_after_sweep(self)

    self.sweep_button.setEnabled(True)
    self.sweep_progress_bar.setVisible(False)
    self.reconnect_button.setEnabled(True)

    QTimer.singleShot(200, self._final_cursor_fix)


# =========================================================
# ERROR HANDLER
# =========================================================

def on_sweep_error(self, msg):

    QMessageBox.critical(self, "Sweep Error", msg)

    self.sweep_button.setEnabled(True)
    self.sweep_progress_bar.setVisible(False)
    self.reconnect_button.setEnabled(True)