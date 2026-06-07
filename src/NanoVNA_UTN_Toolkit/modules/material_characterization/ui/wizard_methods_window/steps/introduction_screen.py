"""
Introduction screen builder (technique selection).

EN: First wizard screen. Populates the technique dropdown from the technique
    registry (``all_descriptors()``) and shows each technique's localized
    description. Selecting a technique stores both ``selected_technique_id``
    (stable id used for dispatch) and ``selected_method`` (localized name kept
    for compatibility with the downstream MeasurementMainWindow).

ES: Primera pantalla del asistente. Arma el desplegable de tecnicas desde el
    registro (``all_descriptors()``) y muestra la descripcion localizada de
    cada tecnica. Al seleccionar una tecnica se guarda ``selected_technique_id``
    (id estable para el despacho) y ``selected_method`` (nombre localizado, que
    se conserva por compatibilidad con la MeasurementMainWindow posterior).
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text, image_path
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import all_descriptors

logger = logging.getLogger(__name__)

# Example setup photos shown in the method detail (per technique).
_TECHNIQUE_PHOTOS = {
    "open_coax_liquids": ["probe_setup_example_1.png", "probe_setup_example_2.png"],
}


def build_introduction_screen(self):
    texts = load_text("characterization_methods.json")
    methods = texts.get("methods", {})

    self.title_label.setText(texts.get("title", "Characterization Methods"))
    self.next_button.setText("▶▶")
    self.next_button.setEnabled(False)
    self.clear_content()

    top = QVBoxLayout()
    top.setSpacing(15)
    top.setContentsMargins(0, 0, 0, 0)

    method_label = QLabel(texts.get("select_label", "Select Characterization Method:"))
    method_label.setStyleSheet("font-size: 16px; font-weight: bold;")
    top.addWidget(method_label)

    self.method_dropdown = QComboBox()
    self.method_dropdown.setEditable(False)
    self.method_dropdown.setStyleSheet("""
        QComboBox {
            background-color: #3b3b3b;
            color: white;
            border: 2px solid white;
            border-radius: 6px;
            padding: 8px;
            font-size: 14px;
            min-width: 380px;
            max-width: 450px;
        }
        QComboBox:hover { background-color: #4d4d4d; }
        QComboBox::drop-down { width: 0px; border: none; background: transparent; }
        QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
    """)

    # Placeholder first item: selectable (selecting it disables Next).
    self.method_dropdown.addItem(texts.get("dropdown_placeholder", "Select Characterization Method"))
    placeholder_item = self.method_dropdown.model().item(0)
    placeholder_item.setForeground(QColor(120, 120, 120))

    # One entry per registered technique. Store ids parallel to the combo.
    descriptors = all_descriptors()
    self._technique_ids = [None]  # index 0 = placeholder
    for desc in descriptors:
        name = methods.get(desc.name_token, {}).get("title", desc.id)
        self.method_dropdown.addItem(name)
        self._technique_ids.append(desc.id)

    top.addWidget(self.method_dropdown)

    # Detail area: description text (left) + example setup photos (right).
    detail_row = QHBoxLayout()

    self.method_info = QTextEdit()
    self.method_info.setReadOnly(True)
    self.method_info.setMinimumHeight(360)
    self.method_info.setStyleSheet("""
        QTextEdit {
            background-color: #2b2b2b;
            color: #dddddd;
            border: 2px solid #555555;
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
        }
    """)
    self.method_info.setText(texts.get("empty_description", ""))
    detail_row.addWidget(self.method_info, stretch=3)

    photos_col = QVBoxLayout()
    self._method_photo_labels = [QLabel(), QLabel()]
    for lbl in self._method_photo_labels:
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setVisible(False)
        photos_col.addWidget(lbl)
    photos_col.addStretch(1)
    photos_container = QWidget()
    photos_container.setLayout(photos_col)
    detail_row.addWidget(photos_container, stretch=2)

    top.addLayout(detail_row)

    def _show_photos(technique_id):
        files = _TECHNIQUE_PHOTOS.get(technique_id, [])
        for lbl, fname in zip(self._method_photo_labels, files + [None, None]):
            if fname:
                pix = QPixmap(image_path(fname))
                if not pix.isNull():
                    lbl.setPixmap(pix.scaledToWidth(320, Qt.SmoothTransformation))
                    lbl.setVisible(True)
                    continue
            lbl.clear()
            lbl.setVisible(False)

    def on_method_changed(index):
        if index <= 0 or index >= len(self._technique_ids):
            self.selected_technique_id = None
            self.selected_method = None
            self.method_info.setText(texts.get("empty_description", ""))
            _show_photos(None)
            self.next_button.setEnabled(False)
            return

        technique_id = self._technique_ids[index]
        self.selected_technique_id = technique_id
        self.selected_method = self.method_dropdown.itemText(index)
        self.next_button.setEnabled(True)

        description = methods.get(technique_id, {}).get("description", "")
        self.method_info.setText(description)
        _show_photos(technique_id)
        logger.info("[CharacterizationWizard] Selected technique: %s", technique_id)

    self.method_dropdown.activated.connect(on_method_changed)

    container = QWidget()
    container.setLayout(top)
    self.content_layout.addWidget(container, alignment=Qt.AlignTop)
