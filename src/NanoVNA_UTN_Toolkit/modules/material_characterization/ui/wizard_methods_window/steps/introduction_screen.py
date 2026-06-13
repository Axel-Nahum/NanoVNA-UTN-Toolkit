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

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QTextEdit, QVBoxLayout, QWidget

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text, image_path
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import all_descriptors

logger = logging.getLogger(__name__)

_TECHNIQUE_PHOTOS = {
    "open_coax_liquids": ["probe_setup_example_1.png", "probe_setup_example_2.png"],
}


class _ScaledImageLabel(QLabel):
    """QLabel that rescales its pixmap to fill available space. Never requests extra space."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        return QSize(0, 0)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def setSourcePixmap(self, pixmap):
        self._source = pixmap
        self._rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._source and not self._source.isNull() and self.width() > 0 and self.height() > 0:
            self.setPixmap(
                self._source.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )


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
    self.method_dropdown.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    self.method_dropdown.setMaximumWidth(500)
    self.method_dropdown.setStyleSheet("""
        QComboBox {
            background-color: #3b3b3b;
            color: white;
            border: 2px solid white;
            border-radius: 6px;
            padding: 8px;
            font-size: 14px;
        }
        QComboBox:hover { background-color: #4d4d4d; }
        QComboBox::drop-down { width: 0px; border: none; background: transparent; }
        QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
        QComboBox QAbstractItemView {
            background-color: #3b3b3b;
            color: white;
            selection-background-color: #4d4d4d;
            border: 1px solid white;
        }
    """)

    self.method_dropdown.addItem(texts.get("dropdown_placeholder", "Select Characterization Method"))
    placeholder_item = self.method_dropdown.model().item(0)
    placeholder_item.setForeground(QColor(120, 120, 120))

    descriptors = all_descriptors()
    self._technique_ids = [None]
    for desc in descriptors:
        name = methods.get(desc.name_token, {}).get("title", desc.id)
        self.method_dropdown.addItem(name)
        self._technique_ids.append(desc.id)

    top.addWidget(self.method_dropdown)

    # Info box: text on top, photos row fixed-height at bottom.
    info_box = QWidget()
    info_box.setObjectName("infoBox")
    info_box.setStyleSheet("""
        QWidget#infoBox {
            background-color: #2b2b2b;
            border: 2px solid #555555;
            border-radius: 8px;
        }
    """)
    info_box_layout = QVBoxLayout(info_box)
    info_box_layout.setContentsMargins(12, 12, 12, 12)
    info_box_layout.setSpacing(10)

    self.method_info = QTextEdit()
    self.method_info.setReadOnly(True)
    self.method_info.setStyleSheet("""
        QTextEdit {
            background-color: #2b2b2b;
            color: #dddddd;
            border: none;
            font-size: 14px;
        }
    """)
    self.method_info.setText(texts.get("empty_description", ""))
    info_box_layout.addWidget(self.method_info, stretch=1)  # texto 1/3, fotos 2/3 del info box

    # Photos row — fixed height so it never affects the window size.
    photos_row = QHBoxLayout()
    photos_row.setSpacing(15)
    photos_row.setContentsMargins(0, 0, 0, 0)
    self._method_photo_labels = [_ScaledImageLabel(), _ScaledImageLabel()]
    for lbl in self._method_photo_labels:
        lbl.setVisible(False)
        lbl.setStyleSheet("border: 1px solid #555555; border-radius: 6px;")
        photos_row.addWidget(lbl)

    photos_row_widget = QWidget()
    photos_row_widget.setObjectName("photosRow")
    photos_row_widget.setStyleSheet("QWidget#photosRow { background-color: #2b2b2b; border: none; }")
    photos_row_widget.setLayout(photos_row)
    photos_row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    photos_row_widget.setMinimumHeight(0)
    photos_row_widget.setVisible(False)
    self._photos_row_widget = photos_row_widget
    info_box_layout.addWidget(photos_row_widget, stretch=2)

    top.addWidget(info_box, stretch=1)

    def _show_photos(technique_id):
        files = _TECHNIQUE_PHOTOS.get(technique_id, [])
        any_loaded = False
        for lbl, fname in zip(self._method_photo_labels, files + [None, None]):
            if fname:
                pix = QPixmap(image_path(fname))
                if not pix.isNull():
                    lbl.setSourcePixmap(pix)
                    lbl.setVisible(True)
                    any_loaded = True
                    continue
            lbl.setSourcePixmap(None)
            lbl.clear()
            lbl.setVisible(False)
        self._photos_row_widget.setVisible(any_loaded)

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
    self.content_layout.addWidget(container)
