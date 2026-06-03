from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

save_auto_scale_data = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale", "save_auto_scale_data")

def show_y_range_dialog(self, target_ax):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

    if target_ax is None:
        QMessageBox.warning(None, "Error", "No axis selected.")
        return

    if self.left_graph_type != "Smith Diagram" or self.right_graph_type != "Smith Diagram": 

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
        ymin_edit.setPlaceholderText(str(target_ax.get_ylim()[0]))
        l1.addWidget(ymin_edit)
        layout.addLayout(l1)

        l2 = QHBoxLayout()
        l2.addWidget(QLabel(f"{self.set_range_y_max}"))
        ymax_edit = QLineEdit()
        ymax_edit.setPlaceholderText(str(target_ax.get_ylim()[1]))
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

                ymin = float(ymin_text) if ymin_text else target_ax.get_ylim()[0]
                ymax = float(ymax_text) if ymax_text else target_ax.get_ylim()[1]

                save_auto_scale_data(self, ymin, ymax, target_ax)

                target_ax.set_ylim(ymin, ymax)
                target_ax.figure.canvas.draw_idle()
                dlg.accept()

            except ValueError:
                QMessageBox.warning(dlg, "Invalid Input", "Please enter valid numbers for Y min and Y max.")

        apply_btn.clicked.connect(apply_clicked)
        cancel_btn.clicked.connect(dlg.reject)

        dlg.exec()