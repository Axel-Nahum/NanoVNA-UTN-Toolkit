from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

save_auto_scale_data = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale", "save_auto_scale_data")
get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

_PM_EXE = "INI/dut_measurement/plot_manager/plot_manager.ini"
_PM_DEV = "modules/dut_measurement/ui/utils/menu/plot_menu/plot_manager/plot_manager.ini"

def _pm_settings(caller_path):
    return get_settings(_PM_EXE, _PM_DEV, caller_path)

def show_y_range_dialog(self, target_ax):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

    if target_ax is None:
        QMessageBox.warning(None, "Error", "No axis selected.")
        return

    if self.left_graph_type != "Smith Diagram" or self.right_graph_type != "Smith Diagram":

        is_left = (target_ax == self.ax_left)
        autoscale_off = not (self.auto_scale_enabled_left if is_left else self.auto_scale_enabled_right)

        init_ymin, init_ymax = target_ax.get_ylim()

        if autoscale_off:
            pm = _pm_settings(Path(__file__).resolve())
            key_min = "set_range/ymin_left" if is_left else "set_range/ymin_right"
            key_max = "set_range/ymax_left" if is_left else "set_range/ymax_right"
            saved_ymin = pm.value(key_min, None, type=float)
            saved_ymax = pm.value(key_max, None, type=float)
            if saved_ymin is not None and saved_ymax is not None:
                init_ymin = saved_ymin
                init_ymax = saved_ymax

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{self.set_range_window_title}")
        dlg.setFixedSize(260, 160)

        layout = QVBoxLayout(dlg)

        hint_label = QLabel("Enter the desired minimum and maximum Y-axis values:")
        hint_label.setStyleSheet("color: gray; font-size: 9pt;")
        hint_label.setWordWrap(True)

        layout.addWidget(hint_label)

        layout.addSpacing(10)

        # --- Inputs ---
        l1 = QHBoxLayout()
        l1.addWidget(QLabel(f"Y min:"))
        ymin_edit = QLineEdit()
        ymin_edit.setText(f"{init_ymin:.6g}")
        l1.addWidget(ymin_edit)
        layout.addLayout(l1)

        l2 = QHBoxLayout()
        l2.addWidget(QLabel(f"{self.set_range_y_max}"))
        ymax_edit = QLineEdit()
        ymax_edit.setText(f"{init_ymax:.6g}")
        l2.addWidget(ymax_edit)
        layout.addLayout(l2)

        layout.addSpacing(10)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton(f"{self.set_range_apply}")
        cancel_btn = QPushButton(f"{self.set_range_close}")
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # --- Logic ---
        def apply_clicked():
            try:
                ymin_text = ymin_edit.text().strip()
                ymax_text = ymax_edit.text().strip()

                if not ymin_text and not ymax_text:
                    dlg.reject()
                    return

                ymin = float(ymin_text) if ymin_text else init_ymin
                ymax = float(ymax_text) if ymax_text else init_ymax

                save_auto_scale_data(self, ymin, ymax, target_ax)

                pm = _pm_settings(Path(__file__).resolve())
                if is_left:
                    pm.setValue("set_range/ymin_left", ymin)
                    pm.setValue("set_range/ymax_left", ymax)
                else:
                    pm.setValue("set_range/ymin_right", ymin)
                    pm.setValue("set_range/ymax_right", ymax)

                target_ax.set_ylim(ymin, ymax)
                target_ax.figure.canvas.draw_idle()
                dlg.accept()

            except ValueError:
                QMessageBox.warning(dlg, "Invalid Input", "Please enter valid numbers for Y min and Y max.")

        apply_btn.clicked.connect(apply_clicked)
        cancel_btn.clicked.connect(dlg.reject)

        dlg.exec()
