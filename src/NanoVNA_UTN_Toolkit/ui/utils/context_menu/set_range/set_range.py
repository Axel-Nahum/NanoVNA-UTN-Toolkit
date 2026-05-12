def show_y_range_dialog(self, target_ax):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

    if target_ax is None:
        QMessageBox.warning(None, "Error", "No axis selected.")
        return

    if self.left_graph_type != "Smith Diagram" or self.right_graph_type != "Smith Diagram": 

        dlg = QDialog(self)
        dlg.setWindowTitle("NanoVNA UTN Toolkit - Set Y Range")
        dlg.setFixedSize(250, 150)

        layout = QVBoxLayout(dlg)

        # --- Inputs ---
        l1 = QHBoxLayout()
        l1.addWidget(QLabel("Y min:"))
        ymin_edit = QLineEdit()
        ymin_edit.setPlaceholderText(str(target_ax.get_ylim()[0]))
        l1.addWidget(ymin_edit)
        layout.addLayout(l1)

        l2 = QHBoxLayout()
        l2.addWidget(QLabel("Y max:"))
        ymax_edit = QLineEdit()
        ymax_edit.setPlaceholderText(str(target_ax.get_ylim()[1]))
        l2.addWidget(ymax_edit)
        layout.addLayout(l2)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
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

                target_ax.set_ylim(ymin, ymax)
                target_ax.figure.canvas.draw_idle()
                dlg.accept()

            except ValueError:
                QMessageBox.warning(dlg, "Invalid Input", "Please enter valid numbers for Y min and Y max.")

        apply_btn.clicked.connect(apply_clicked)
        cancel_btn.clicked.connect(dlg.reject)

        dlg.exec()