from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
import os
import shutil

from pathlib import Path

from datetime import datetime

from PySide6.QtWidgets import (
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QDialogButtonBox
)

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

get_calibration_path = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils", "get_calibration_path")

# ---------------------------------------------------------------------------------------------------------------- #

class _SaveKitDialog(QDialog):
    """Dialog that lets the user name a calibration kit and choose where to save it."""

    def __init__(self, parent, default_name):
        super().__init__(parent)
        self.setWindowTitle("Save Calibration Kit")
        self.setMinimumWidth(440)

        self._name = None
        self._save_internal = True
        self._save_custom = False

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Kit name:"))
        self._name_edit = QLineEdit(default_name)
        layout.addWidget(self._name_edit)

        self._cb_internal = QCheckBox(
            "Save to internal library  (available in the calibration selector on startup)"
        )
        self._cb_internal.setChecked(True)

        self._cb_custom = QCheckBox(
            "Export to a custom folder  (backup or transfer to another computer)"
        )
        self._cb_custom.setChecked(False)

        layout.addWidget(self._cb_internal)
        layout.addWidget(self._cb_custom)

        hint = QLabel(
            "The exported ZIP contains the calibration error files and a metadata file.\n"
            "Can be imported later using File → Import Calibration."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #888888; font-style: italic; margin-left: 20px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Save")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self):
        if not self._cb_internal.isChecked() and not self._cb_custom.isChecked():
            QMessageBox.warning(self, "No option selected", "Please select at least one save option.")
            return
        self._name = self._name_edit.text().strip()
        self._save_internal = self._cb_internal.isChecked()
        self._save_custom = self._cb_custom.isChecked()
        self.accept()

    @property
    def kit_name(self):
        return self._name

    @property
    def save_internal(self):
        return self._save_internal

    @property
    def save_custom(self):
        return self._save_custom


def show_calibration_warning(self):
    msg = QMessageBox(self)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("No calibration available")
    msg.setText(
        "No calibration has been performed in this session.\n\n"
        "Run the calibration wizard first, then use Save Kit to store the results."
    )
    msg.exec()

def save_kit_dialog(self):
    from PySide6.QtWidgets import QMessageBox
    """Shows a dialog to save the calibration without advancing to graphics window"""

    self.osm_calibration.is_complete_true()
    self.thru_calibration.is_complete_true()

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

    files = [
        os.path.join(osm_dir, "open.s1p"),
        os.path.join(osm_dir, "short.s1p"),
        os.path.join(osm_dir, "match.s1p"),
        os.path.join(thru_dir, "thru.s2p")
    ]

    # Load configuration for calibration

    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    # Method
    selected_method = settings.value("Calibration/Method", "No Kit")

    # Dialog to enter calibration name
    from PySide6.QtWidgets import QInputDialog

    _prefix_map = {
        "OSM (Open - Short - Match)": "OSM",
        "Thru Normalization": "Thru_Normalization",
        "Open/Short Normalization": "OpenShort_Normalization",
        "1-Port+N": "1PortN",
        "Enhanced-Response": "Enhanced_Response",
    }
    prefix = _prefix_map.get(selected_method, "Calibration")

    dlg = _SaveKitDialog(
        self,
        default_name=f"{prefix}_Calibration_{self.get_current_timestamp()}"
    )
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    name = dlg.kit_name
    save_internal = dlg.save_internal
    save_custom = dlg.save_custom

    if not name:
        return

    dest_root = None
    if save_custom:
        from PySide6.QtWidgets import QFileDialog
        dest_root = QFileDialog.getExistingDirectory(
            self, "Select folder to export calibration kit"
        )
        if not dest_root:
            return

    if name:
        try:
            import zipfile

            # --- Save to internal library ---
            if selected_method not in ("Thru Normalization", "Open/Short Normalization"):
                self.osm_calibration.save_calibration_file(name, selected_method, False, files)
                logging.info(f"[save_kit_dialog] OSM kit '{name}' saved")

            self.thru_calibration.save_calibration_file(name, selected_method, True, files, osm_instance=self.osm_calibration)
            logging.info(f"[save_kit_dialog] THRU kit '{name}' saved")

            # --- Register in INI ---
            settings_calibration = get_settings(
                "INI/dut_measurement/dut_measurement/calibration_config/calibration_config.ini",
                "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                Path(__file__).resolve()
            )

            existing_groups = settings_calibration.childGroups()
            for g in existing_groups:
                if g.startswith("Kit_"):
                    if settings_calibration.value(f"{g}/kit_name", "") == name:
                        QMessageBox.warning(self, "Duplicate name",
                                            f"A kit named '{name}' already exists. Please choose another name.")
                        return

            if getattr(self, 'last_saved_kit_id', None):
                next_id = self.last_saved_kit_id
            else:
                kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
                next_id = max(kit_ids, default=0) + 1
                self.last_saved_kit_id = next_id

            calibration_entry_name = f"Kit_{next_id}"
            full_calibration_name = f"{name}_{next_id}"
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            sweep_settings = get_settings(
                "INI/dut_measurement/sweep_config/sweep_config.ini",
                "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini",
                Path(__file__).resolve()
            )

            settings_calibration.beginGroup(calibration_entry_name)
            settings_calibration.setValue("kit_name", name)
            settings_calibration.setValue("method", selected_method)
            settings_calibration.setValue("id", next_id)
            settings_calibration.setValue("DateTime_Kits", current_datetime)
            settings_calibration.setValue("StartFreqHz", sweep_settings.value("Frequency/StartFreqHz", 0, type=int))
            settings_calibration.setValue("StopFreqHz", sweep_settings.value("Frequency/StopFreqHz", 0, type=int))
            settings_calibration.setValue("Segments", sweep_settings.value("Frequency/Segments", 101, type=int))
            settings_calibration.setValue("StartUnit", sweep_settings.value("Frequency/StartUnit", "MHz"))
            settings_calibration.setValue("StopUnit", sweep_settings.value("Frequency/StopUnit", "MHz"))
            settings_calibration.endGroup()

            settings_calibration.beginGroup("Calibration")
            settings_calibration.setValue("Name", full_calibration_name)
            settings_calibration.endGroup()
            settings_calibration.sync()

            logging.info(f"[save_kit_dialog] Registered calibration {full_calibration_name}")

            # --- Single final message ---
            if save_custom:
                kits_base = get_calibration_path(
                    "modules/dut_measurement/calibration/kits",
                    "modules/dut_measurement/calibration/kits",
                    Path(__file__).resolve()
                )
                kit_folder = os.path.join(kits_base, name)

                ini_lines = [
                    "[Kit]\n",
                    f"name = {name}\n",
                    f"method = {selected_method}\n",
                    f"date = {current_datetime}\n",
                    f"start_freq_hz = {sweep_settings.value('Frequency/StartFreqHz', 0)}\n",
                    f"stop_freq_hz = {sweep_settings.value('Frequency/StopFreqHz', 0)}\n",
                    f"segments = {sweep_settings.value('Frequency/Segments', 101)}\n",
                    f"start_unit = {sweep_settings.value('Frequency/StartUnit', 'MHz')}\n",
                    f"stop_unit = {sweep_settings.value('Frequency/StopUnit', 'MHz')}\n",
                ]

                zip_path = os.path.join(dest_root, f"{name}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    if os.path.isdir(kit_folder):
                        for root, dirs, fnames in os.walk(kit_folder):
                            for fname in fnames:
                                fpath = os.path.join(root, fname)
                                arcname = os.path.relpath(fpath, kit_folder)
                                zf.write(fpath, arcname)
                    zf.writestr("kit_info.ini", "".join(ini_lines))

                logging.info(f"[save_kit_dialog] Exported ZIP: {zip_path}")
                if save_internal:
                    msg = f"Kit '{name}' saved to the internal library and exported as:\n{zip_path}"
                else:
                    msg = f"Kit '{name}' exported as:\n{zip_path}"
                QMessageBox.information(self, "Calibration kit saved", msg)
            else:
                QMessageBox.information(
                    self, "Calibration kit saved",
                    f"Kit '{name}' saved to the internal library."
                )

        except Exception as e:
            logging.error(f"[CalibrationKit] Error saving calibration: {e}")
            QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")


def export_loaded_kit_dialog(self):
    """Export the currently loaded kit as a ZIP (only available when a kit is active)."""
    from PySide6.QtWidgets import QMessageBox, QFileDialog
    import zipfile

    settings_cal = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    kit_ok = settings_cal.value("Calibration/Kits", False, type=bool)
    if not kit_ok:
        QMessageBox.warning(
            self, "No kit loaded",
            "No calibration kit is currently active.\n\n"
            "Select a kit first using Calibration → Select Kit."
        )
        return

    kit_name_full = settings_cal.value("Calibration/Name", "")
    base_name = kit_name_full.rsplit("_", 1)[0] if "_" in kit_name_full else kit_name_full

    if not base_name:
        QMessageBox.warning(self, "No kit loaded", "Could not determine the active kit name.")
        return

    kits_base = get_calibration_path(
        "modules/dut_measurement/calibration/kits",
        "modules/dut_measurement/calibration/kits",
        Path(__file__).resolve()
    )
    kit_folder = os.path.join(kits_base, base_name)

    if not os.path.isdir(kit_folder):
        QMessageBox.warning(
            self, "Kit folder not found",
            f"The kit folder could not be located:\n{kit_folder}"
        )
        return

    dest_root = QFileDialog.getExistingDirectory(self, "Select folder to export calibration kit")
    if not dest_root:
        return

    # Build kit_info.ini from stored settings
    kit_group = None
    for g in settings_cal.childGroups():
        if g.startswith("Kit_") and settings_cal.value(f"{g}/kit_name", "") == base_name:
            kit_group = g
            break

    if kit_group:
        settings_cal.beginGroup(kit_group)
        method = settings_cal.value("method", "")
        date = settings_cal.value("DateTime_Kits", "")
        start_hz = settings_cal.value("StartFreqHz", 0)
        stop_hz = settings_cal.value("StopFreqHz", 0)
        segments = settings_cal.value("Segments", 101)
        start_unit = settings_cal.value("StartUnit", "MHz")
        stop_unit = settings_cal.value("StopUnit", "MHz")
        settings_cal.endGroup()
    else:
        method = settings_cal.value("Calibration/Method", "")
        date = ""
        start_hz = stop_hz = 0
        segments = 101
        start_unit = stop_unit = "MHz"

    # Fall back to current sweep config when frequency not stored in the kit group
    if not int(float(start_hz or 0)) or not int(float(stop_hz or 0)):
        sweep_s = get_settings(
            "INI/dut_measurement/sweep_config/sweep_config.ini",
            "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini",
            Path(__file__).resolve()
        )
        start_hz   = sweep_s.value("Frequency/StartFreqHz", 50000)
        stop_hz    = sweep_s.value("Frequency/StopFreqHz",  1500000000)
        segments   = sweep_s.value("Frequency/Segments",    101)
        start_unit = sweep_s.value("Frequency/StartUnit",   "kHz")
        stop_unit  = sweep_s.value("Frequency/StopUnit",    "GHz")

    ini_lines = [
        "[Kit]\n",
        f"name = {base_name}\n",
        f"method = {method}\n",
        f"date = {date}\n",
        f"start_freq_hz = {start_hz}\n",
        f"stop_freq_hz = {stop_hz}\n",
        f"segments = {segments}\n",
        f"start_unit = {start_unit}\n",
        f"stop_unit = {stop_unit}\n",
    ]

    try:
        import re
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = re.sub(r'_\d{8}_\d{6}$', '', base_name)
        zip_path = os.path.join(dest_root, f"{clean_name}_{ts}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, fnames in os.walk(kit_folder):
                for fname in fnames:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, kit_folder)
                    zf.write(fpath, arcname)
            zf.writestr("kit_info.ini", "".join(ini_lines))

        logging.info(f"[export_loaded_kit_dialog] Exported: {zip_path}")
        QMessageBox.information(
            self, "Kit exported",
            f"Kit '{base_name}' exported as:\n{zip_path}"
        )
    except Exception as e:
        logging.error(f"[export_loaded_kit_dialog] Error: {e}")
        QMessageBox.critical(self, "Error", f"Error exporting kit: {str(e)}")


class _ImportKitDialog(QDialog):
    """Dialog shown when importing a calibration kit ZIP."""

    def __init__(self, parent, zip_name, kit_info: dict):
        super().__init__(parent)
        self.setWindowTitle("Import Calibration Kit")
        self.setMinimumWidth(420)

        self._final_name = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Kit found in ZIP:"))

        self._name_edit = QLineEdit(zip_name)
        self._name_edit.setEnabled(False)
        self._name_edit.setStyleSheet(
            "QLineEdit:disabled { color: #6b7fa3; border: 1px solid #3a3a5a; }"
            "QLineEdit:enabled  { color: #e0e0e0; border: 1px solid #555577; }"
        )
        layout.addWidget(self._name_edit)

        self._cb_rename = QCheckBox("Use a custom name")
        self._cb_rename.toggled.connect(self._on_rename_toggled)
        layout.addWidget(self._cb_rename)

        # Metadata summary
        def _auto_fmt(hz):
            try:
                hz = float(hz)
            except (TypeError, ValueError):
                return str(hz)
            if hz >= 1e9:   return f"{hz / 1e9:g} GHz"
            elif hz >= 1e6: return f"{hz / 1e6:g} MHz"
            elif hz >= 1e3: return f"{hz / 1e3:g} kHz"
            else:           return f"{hz:g} Hz"

        method = kit_info.get("method", "")
        date   = kit_info.get("date", "")
        start  = kit_info.get("start_freq_hz", "")
        stop   = kit_info.get("stop_freq_hz", "")
        segs   = kit_info.get("segments", "")

        info_lines = []
        if method:
            info_lines.append(f"Method: {method}")
        if date:
            info_lines.append(f"Calibrated: {date}")
        try:
            s_hz = float(start)
            e_hz = float(stop)
            if s_hz and e_hz:
                info_lines.append(f"Frequency: {_auto_fmt(s_hz)} – {_auto_fmt(e_hz)},  {segs} pts")
        except (TypeError, ValueError):
            pass

        if info_lines:
            info_lbl = QLabel("\n".join(info_lines))
            info_lbl.setStyleSheet("font-size: 11px; color: #888888; font-style: italic;")
            info_lbl.setWordWrap(True)
            layout.addWidget(info_lbl)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Import")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_rename_toggled(self, checked):
        self._name_edit.setEnabled(checked)
        if checked:
            self._name_edit.setFocus()
            self._name_edit.selectAll()

    def _on_ok(self):
        self._final_name = self._name_edit.text().strip()
        self.accept()

    @property
    def kit_name(self):
        return self._final_name


def import_kit_dialog(self):
    """Import a calibration kit from a ZIP file previously exported with Export Kit."""
    import zipfile
    import configparser
    from PySide6.QtWidgets import QMessageBox, QFileDialog

    zip_path, _ = QFileDialog.getOpenFileName(
        self, "Select calibration kit ZIP", "", "ZIP files (*.zip)"
    )
    if not zip_path:
        return

    # --- Read kit_info.ini from ZIP ---
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            if "kit_info.ini" not in zf.namelist():
                QMessageBox.warning(
                    self, "Invalid kit file",
                    "The selected ZIP does not contain a kit_info.ini.\n"
                    "Make sure it was exported using File → Export Kit."
                )
                return
            ini_bytes = zf.read("kit_info.ini").decode("utf-8")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Could not open ZIP:\n{e}")
        return

    cfg = configparser.ConfigParser()
    cfg.read_string(ini_bytes)
    kit_info = dict(cfg["Kit"]) if "Kit" in cfg else {}

    zip_kit_name = kit_info.get("name", "") or os.path.splitext(os.path.basename(zip_path))[0]

    # --- Ask user for final name ---
    dlg = _ImportKitDialog(self, zip_kit_name, kit_info)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    name = dlg.kit_name
    if not name:
        return

    # --- Check for duplicate name ---
    settings_cal = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )
    existing_groups = settings_cal.childGroups()
    for g in existing_groups:
        if g.startswith("Kit_") and settings_cal.value(f"{g}/kit_name", "") == name:
            QMessageBox.warning(self, "Duplicate name",
                                f"A kit named '{name}' already exists. Please choose another name.")
            return

    # --- Extract ZIP to kits/<name>/ ---
    kits_base = get_calibration_path(
        "modules/dut_measurement/calibration/kits",
        "modules/dut_measurement/calibration/kits",
        Path(__file__).resolve()
    )
    kit_folder = os.path.join(kits_base, name)

    try:
        os.makedirs(kit_folder, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                if member == "kit_info.ini":
                    continue
                zf.extract(member, kit_folder)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Could not extract kit:\n{e}")
        return

    # --- Register in calibration_config.ini ---
    kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
    next_id = max(kit_ids, default=0) + 1
    calibration_entry_name = f"Kit_{next_id}"
    full_calibration_name = f"{name}_{next_id}"
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    method     = kit_info.get("method", "")
    start_hz   = kit_info.get("start_freq_hz", 0)
    stop_hz    = kit_info.get("stop_freq_hz", 0)
    segments   = kit_info.get("segments", 101)
    start_unit = kit_info.get("start_unit", "MHz")
    stop_unit  = kit_info.get("stop_unit", "MHz")

    settings_cal.beginGroup(calibration_entry_name)
    settings_cal.setValue("kit_name", name)
    settings_cal.setValue("method", method)
    settings_cal.setValue("id", next_id)
    settings_cal.setValue("DateTime_Kits", current_datetime)
    settings_cal.setValue("StartFreqHz", int(float(start_hz)) if start_hz else 0)
    settings_cal.setValue("StopFreqHz",  int(float(stop_hz))  if stop_hz  else 0)
    settings_cal.setValue("Segments",    int(segments))
    settings_cal.setValue("StartUnit",   start_unit)
    settings_cal.setValue("StopUnit",    stop_unit)
    settings_cal.endGroup()

    if method == "OSM (Open - Short - Match)":
        parameter = "S11"
    elif method == "Thru Normalization":
        parameter = "S21"
    elif method == "Open/Short Normalization":
        parameter = "S11"
    else:
        parameter = "S11, S21"

    settings_cal.beginGroup("Calibration")
    settings_cal.setValue("Name", full_calibration_name)
    settings_cal.setValue("id", next_id)
    settings_cal.setValue("Method", method)
    settings_cal.setValue("DateTime_Kits", current_datetime)
    settings_cal.setValue("Kits", True)
    settings_cal.setValue("NoCalibration", False)
    settings_cal.setValue("Parameter", parameter)
    settings_cal.endGroup()
    settings_cal.sync()

    logging.info(f"[import_kit_dialog] Imported kit '{name}' as {full_calibration_name}")

    # --- Restore sweep range ---
    if start_hz and stop_hz:
        sweep_settings = get_settings(
            "INI/dut_measurement/sweep_config/sweep_config.ini",
            "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini",
            Path(__file__).resolve()
        )
        sweep_settings.setValue("Frequency/StartFreqHz", int(float(start_hz)))
        sweep_settings.setValue("Frequency/StopFreqHz",  int(float(stop_hz)))
        sweep_settings.setValue("Frequency/Segments",    int(segments))
        sweep_settings.setValue("Frequency/StartUnit",   start_unit)
        sweep_settings.setValue("Frequency/StopUnit",    stop_unit)
        sweep_settings.sync()

    # --- Reopen window with new kit active ---
    from NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time import stop_realtime as _stop
    _stop(self)

    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics
    if self.vna_device:
        new_window = NanoVNAGraphics(vna_device=self.vna_device)
    else:
        new_window = NanoVNAGraphics()
    new_window.show()
    self.close()