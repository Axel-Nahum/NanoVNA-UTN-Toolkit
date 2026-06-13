"""
Export Dialog for Graphics Window
Provides functionality to export graph data and images in various formats.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import io
import os
import sys
import matplotlib.pyplot as plt

from pathlib import Path

from matplotlib.patches import FancyBboxPatch

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QMessageBox, QApplication, QFileDialog)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QPixmap

plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['text.usetex'] = False
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'
plt.rcParams['mathtext.rm'] = 'serif'

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

DutResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.dut_resource_loader", "DutResourceLoader")

class ExportDialog(QDialog):
    """Dialog for exporting graph data and images."""

    def __init__(self, parent=None, figure=None, left_graph=None, right_graph=None, freqs = None, show_markers_left=None, show_markers_right=None,
        update_cursor_left = None, update_cursor_right = None):
        super().__init__(parent)

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON
# ------------------------------------------------------------------------------------------------------------------- #

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini",
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

        self.resourceLoader = DutResourceLoader(
            self_window = self,
            module = "dut_measurement",
            lang = current_lang,
            json_resource = "dut_measurement_features.json"
        )

        self.resourceLoader.load_exporters_resources()

# ------------------------------------------------------------------------------------------------------------------- #

        self.left_graph = left_graph
        self.right_grap = right_graph
        self.freqs = freqs

        self.show_markers_left = show_markers_left
        self.show_markers_right = show_markers_right

        self.update_cursor_left = update_cursor_left
        self.update_cursor_right = update_cursor_right

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )

        # QWidget
        background_color = settings.value("Dark_Light/QWidget/background-color", "#3a3a3a")

        # QTabWidget pane
        tabwidget_pane_bg = settings.value("Dark_Light/QTabWidget_pane/background-color", "#3b3b3b")

        # QTabBar
        tabbar_bg = settings.value("Dark_Light/QTabBar/background-color", "#2b2b2b")
        tabbar_color = settings.value("Dark_Light/QTabBar/color", "white")
        tabbar_padding = settings.value("Dark_Light/QTabBar/padding", "5px 12px")
        tabbar_border = settings.value("Dark_Light/QTabBar/border", "none")
        tabbar_border_tl_radius = settings.value("Dark_Light/QTabBar/border-top-left-radius", "6px")
        tabbar_border_tr_radius = settings.value("Dark_Light/QTabBar/border-top-right-radius", "6px")

        # QTabBar selected
        tabbar_selected_bg = settings.value("Dark_Light/QTabBar_selected/background-color", "#4d4d4d")
        tabbar_selected_color = settings.value("Dark_Light/QTabBar/color", "white")

        # QSpinBox
        spinbox_bg = settings.value("Dark_Light/QSpinBox/background-color", "#3b3b3b")
        spinbox_color = settings.value("Dark_Light/QSpinBox/color", "white")
        spinbox_border = settings.value("Dark_Light/QSpinBox/border", "1px solid white")
        spinbox_border_radius = settings.value("Dark_Light/QSpinBox/border-radius", "8px")

        # QGroupBox title
        groupbox_title_color = settings.value("Dark_Light/QGroupBox_title/color", "white")

        # QLabel
        label_color = settings.value("Dark_Light/QLabel/color", "white")

        # QLineEdit
        lineedit_bg = settings.value("Dark_Light/QLineEdit/background-color", "#3b3b3b")
        lineedit_color = settings.value("Dark_Light/QLineEdit/color", "white")
        lineedit_border = settings.value("Dark_Light/QLineEdit/border", "1px solid white")
        lineedit_border_radius = settings.value("Dark_Light/QLineEdit/border-radius", "6px")
        lineedit_padding = settings.value("Dark_Light/QLineEdit/padding", "4px")
        lineedit_focus_bg = settings.value("Dark_Light/QLineEdit_focus/background-color", "#454545")
        lineedit_focus_border = settings.value("Dark_Light/QLineEdit_focus/border", "1px solid #4d90fe")

        # QPushButton
        pushbutton_bg = settings.value("Dark_Light/QPushButton/background-color", "#3b3b3b")
        pushbutton_color = settings.value("Dark_Light/QPushButton/color", "white")
        pushbutton_border = settings.value("Dark_Light/QPushButton/border", "1px solid white")
        pushbutton_border_radius = settings.value("Dark_Light/QPushButton/border-radius", "6px")
        pushbutton_padding = settings.value("Dark_Light/QPushButton/padding", "4px 10px")
        pushbutton_hover_bg = settings.value("Dark_Light/QPushButton_hover/background-color", "#4d4d4d")
        pushbutton_pressed_bg = settings.value("Dark_Light/QPushButton_pressed/background-color", "#5c5c5c")

        # QMenu
        menu_bg = settings.value("Dark_Light/QMenu/background", "#3a3a3a")
        menu_color = settings.value("Dark_Light/QMenu/color", "white")
        menu_border = settings.value("Dark_Light/QMenu/border", "1px solid #3b3b3b")
        menu_item_selected_bg = settings.value("Dark_Light/QMenu::item:selected/background-color", "#4d4d4d")

        # QMenuBar
        menu_item_color = settings.value("Dark_Light/QMenu_item_selected/background-color", "4d4d4d")
        menubar_bg = settings.value("Dark_Light/QMenuBar/background-color", "#3a3a3a")
        menubar_color = settings.value("Dark_Light/QMenuBar/color", "white")
        menubar_item_bg = settings.value("Dark_Light/QMenuBar_item/background", "transparent")
        menubar_item_color = settings.value("Dark_Light/QMenuBar_item/color", "white")
        menubar_item_padding = settings.value("Dark_Light/QMenuBar_item/padding", "4px 10px")
        menubar_item_selected_bg = settings.value("Dark_Light/QMenuBar_item_selected/background-color", "#4d4d4d")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {background_color};
            }}
            QTabWidget::pane {{
                background-color: {tabwidget_pane_bg};
            }}
            QTabBar::tab {{
                background-color: {tabbar_bg};
                color: {tabbar_color};
                padding: {tabbar_padding};
                border: {tabbar_border};
                border-top-left-radius: {tabbar_border_tl_radius};
                border-top-right-radius: {tabbar_border_tr_radius};
            }}
            QMenu{{
                color_ {menubar_color};
                background-color_ {menu_item_color};
            }}
            QTabBar::tab:selected {{
                background-color: {tabbar_selected_bg};
                color: {tabbar_selected_color};
            }}
            QSpinBox {{
                background-color: {spinbox_bg};
                color: {spinbox_color};
                border: {spinbox_border};
                border-radius: {spinbox_border_radius};
            }}
            QGroupBox:title {{
                color: {groupbox_title_color};
            }}
            QLabel {{
                color: {label_color};
            }}
            QLineEdit {{
                background-color: {lineedit_bg};
                color: {lineedit_color};
                border: {lineedit_border};
                border-radius: {lineedit_border_radius};
                padding: {lineedit_padding};
            }}
            QLineEdit:focus {{
                background-color: {lineedit_focus_bg};
                border: {lineedit_focus_border};
            }}
            QPushButton {{
                background-color: {pushbutton_bg};
                color: {pushbutton_color};
                border: {pushbutton_border};
                border-radius: {pushbutton_border_radius};
                padding: {pushbutton_padding};
            }}
            QPushButton:hover {{
                background-color: {pushbutton_hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pushbutton_pressed_bg};
            }}
            QMenuBar {{
                background-color: {menubar_bg};
                color: {menubar_color};
            }}
            QMenuBar::item {{
                background: {menubar_item_bg};
                color: {menubar_item_color};
                padding: {menubar_item_padding};
            }}
            QMenuBar::item:selected {{
                background: {menubar_item_selected_bg};
            }}
            QMenu {{
                background-color: {menu_bg};
                color: {menu_color};
                border: {menu_border};
            }}
            QMenu::item:selected {{
                background-color: {menu_item_color};
            }}
        """)

        self.figure = figure
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface for the export dialog."""
        self.setWindowTitle(f"{self.exporters_window_title}")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Preview section
        preview_label = QLabel(f"{self.exporters_preview_title}")
        layout.addWidget(preview_label)

        # Create and add preview image
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        self.preview_label.setMinimumHeight(300)

        # Generate static preview
        preview_widget = self.create_interactive_preview()
        if preview_widget:
            layout.addWidget(preview_widget)

        # Buttons section
        buttons_layout = QHBoxLayout()

        # Copy to clipboard button
        copy_button = QPushButton(f"{self.exporters_copy_button}")
        copy_button.clicked.connect(self.copy_to_clipboard)
        buttons_layout.addWidget(copy_button)

        # Save as image button
        save_image_button = QPushButton(f"{self.exporters_image_button}")
        save_image_button.clicked.connect(self.save_as_image)
        buttons_layout.addWidget(save_image_button)

        # Save as CSV button
        save_csv_button = QPushButton(f"{self.exporters_csv_button}")
        save_csv_button.clicked.connect(self.save_as_csv)
        buttons_layout.addWidget(save_csv_button)

        layout.addLayout(buttons_layout)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_button = QPushButton(f"{self.exporters_close_button}")
        close_button.clicked.connect(self.close)
        close_layout.addWidget(close_button)
        layout.addLayout(close_layout)

    def create_interactive_preview(self):
        """
        Create an interactive preview QWidget with draggable marker info boxes.
        Markers can be moved anywhere on the canvas and resized from the top-right corner.
        """
        import copy
        import logging
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

        if not self.figure:
            return None

        # --- Make a deep copy of the figure to avoid altering the original ---
        fig_copy = copy.deepcopy(self.figure)

        # --- Keep only main axes, hide smaller axes (like sliders) ---
        axes_to_keep = [ax for ax in fig_copy.axes if ax.get_position().height > 0.1 and ax.get_position().width > 0.1]
        if not axes_to_keep:
            return None
        ax = axes_to_keep[0]

        for ax_sub in fig_copy.axes:
            pos = ax_sub.get_position()
            if pos.height < 0.1 or pos.width < 0.1:
                ax_sub.set_visible(False)

        # --- Load INI settings ---
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
            Path(__file__).resolve()
        )

        # --- Determine active markers dynamically ---
        active_markers = []

        if self.figure == getattr(self.parent_window, 'fig_left', None):
            unit = settings.value("Graphic1/db_times", "dB")
            graph = settings.value("Tab1/GraphType1", "Magnitude")
            for i in range(1, 3):
                cursor = getattr(self.parent_window, f'cursor_left{"_2" if i==2 else ""}', None)
                show_flag = self.show_markers_left[i-1]
                color = settings.value(f"Graphic1/MarkerColor{i}", "red")
                if cursor is not None and show_flag:
                    active_markers.append((cursor, i, color))

        elif self.figure == getattr(self.parent_window, 'fig_right', None):
            unit = settings.value("Graphic2/db_times", "dB")
            graph = settings.value("Tab2/GraphType2", "Magnitude")
            for i in range(1, 3):
                cursor = getattr(self.parent_window, f'cursor_right{"_2" if i==2 else ""}', None)
                show_flag = self.show_markers_right[i-1]
                color = settings.value(f"Graphic2/MarkerColor{i}", "red")
                if cursor is not None and show_flag:
                    active_markers.append((cursor, i, color))

        # --- Create QWidget and embed FigureCanvas ---
        preview_widget = QWidget()
        playout = QVBoxLayout()
        preview_widget.setLayout(playout)
        canvas = FigureCanvas(fig_copy)
        canvas.setMinimumSize(600, 400)
        playout.addWidget(canvas)
        self.preview_canvas = canvas

        # --- Add marker boxes (text + FancyBboxPatch) ---
        ann_objects = []  # list of {'text': txt, 'patch': patch}

        if active_markers:
            canvas.draw()

            def format_frequency(freq_mhz):
                if freq_mhz >= 1000.0:
                    return freq_mhz / 1000.0, "GHz"
                elif freq_mhz >= 1.0:
                    return freq_mhz, "MHz"
                else:
                    return freq_mhz * 1000.0, "kHz"

            def _build_text(marker_id, x_data, y_data):
                freq_val, freq_unit = format_frequency(x_data[0])
                if graph == "Smith Diagram":
                    return (f"Marker {marker_id}\n"
                            f"Re:   {x_data[0]:.4f}\n"
                            f"Im:   {y_data[0]:.4f}")
                elif graph == "Phase":
                    return (f"Marker {marker_id}\n"
                            f"Freq: {freq_val:.3f} {freq_unit}\n"
                            f"φ:    {y_data[0]:.3f}°")
                else:
                    val_label = "|S|:" if unit == "dB" else "|S|:"
                    unit_str  = f" {unit}" if unit == "dB" else ""
                    return (f"Marker {marker_id}\n"
                            f"Freq: {freq_val:.3f} {freq_unit}\n"
                            f"{val_label} {y_data[0]:.4f}{unit_str}")

            PAD = 8

            def _make_patch(txt_obj, ann_x, ann_y):
                renderer = canvas.get_renderer()
                tbbox = txt_obj.get_window_extent(renderer=renderer)
                try:
                    d_lb = ax.transData.inverted().transform((tbbox.x0 - PAD, tbbox.y0 - PAD))
                    d_rt = ax.transData.inverted().transform((tbbox.x1 + PAD, tbbox.y1 + PAD))
                except Exception:
                    d_lb = (ann_x - 0.15, ann_y - 0.08)
                    d_rt = (ann_x + 0.15, ann_y + 0.08)
                return d_lb, d_rt

            for cursor, marker_id, color in active_markers:
                x_data, y_data = cursor.get_data()
                if len(x_data) == 0 or len(y_data) == 0:
                    continue

                ann_x, ann_y = x_data[0], y_data[0]
                text = _build_text(marker_id, x_data, y_data)

                txt = ax.text(ann_x, ann_y, text,
                              ha='center', va='center',
                              color=color, fontsize=9,
                              linespacing=1.8, family='monospace',
                              zorder=10, clip_on=False)

                d_lb, d_rt = _make_patch(txt, ann_x, ann_y)
                patch = FancyBboxPatch(
                    (d_lb[0], d_lb[1]),
                    max(1e-9, d_rt[0] - d_lb[0]),
                    max(1e-9, d_rt[1] - d_lb[1]),
                    boxstyle='square,pad=0',
                    facecolor='white', edgecolor=color,
                    alpha=0.9, transform=ax.transData,
                    zorder=9, clip_on=False
                )
                ax.add_patch(patch)
                ann_objects.append({'text': txt, 'patch': patch})

        canvas.draw_idle()

        # --- Drag / resize (all edges + corners, works anywhere on canvas) ---
        drag_state = {
            "obj": None, "mode": None, "press_px": None,
            "edge": None, "bbox0_px": None,
            "fontsize0": None, "text_w0": None, "text_h0": None,
            "patch_xy0": None, "txt_pos0": None,
        }

        EDGE_TOL = 10
        MIN_W_PX, MIN_H_PX = 50, 35

        def _patch_px(patch):
            t = patch.get_transform()
            lb = t.transform((patch.get_x(), patch.get_y()))
            rt = t.transform((patch.get_x() + patch.get_width(),
                              patch.get_y() + patch.get_height()))
            return lb[0], lb[1], rt[0], rt[1]

        def _px_to_data(px, py):
            return tuple(ax.transData.inverted().transform((px, py)))

        def _detect_edge(L, B, R, T, mx, my):
            on_l = abs(mx - L) < EDGE_TOL
            on_r = abs(mx - R) < EDGE_TOL
            on_b = abs(my - B) < EDGE_TOL
            on_t = abs(my - T) < EDGE_TOL
            in_x = L + EDGE_TOL < mx < R - EDGE_TOL
            in_y = B + EDGE_TOL < my < T - EDGE_TOL
            if on_r and on_t: return "top_right"
            if on_l and on_t: return "top_left"
            if on_r and on_b: return "bot_right"
            if on_l and on_b: return "bot_left"
            if on_r and in_y: return "right"
            if on_l and in_y: return "left"
            if on_t and in_x: return "top"
            if on_b and in_x: return "bottom"
            return None

        def _edge_cursor(edge):
            if edge in ("left", "right"):          return Qt.SizeHorCursor
            if edge in ("top", "bottom"):          return Qt.SizeVerCursor
            if edge in ("top_right", "bot_left"):  return Qt.SizeBDiagCursor
            if edge in ("top_left",  "bot_right"): return Qt.SizeFDiagCursor
            return Qt.ArrowCursor

        def _inside(L, B, R, T, mx, my):
            return L + EDGE_TOL < mx < R - EDGE_TOL and B + EDGE_TOL < my < T - EDGE_TOL

        def on_move_hover(event):
            if drag_state["obj"] is not None:
                return
            for obj in ann_objects:
                L, B, R, T = _patch_px(obj['patch'])
                edge = _detect_edge(L, B, R, T, event.x, event.y)
                if edge:
                    canvas.setCursor(_edge_cursor(edge))
                    return
                if _inside(L, B, R, T, event.x, event.y):
                    canvas.setCursor(Qt.OpenHandCursor)
                    return
            canvas.setCursor(Qt.ArrowCursor)

        def on_press(event):
            for obj in ann_objects:
                patch = obj['patch']
                txt   = obj['text']
                L, B, R, T = _patch_px(patch)
                edge = _detect_edge(L, B, R, T, event.x, event.y)
                if edge:
                    renderer = canvas.get_renderer()
                    tbbox = txt.get_window_extent(renderer=renderer)
                    drag_state.update({
                        "obj": obj, "mode": "resize",
                        "press_px": (event.x, event.y),
                        "edge": edge,
                        "bbox0_px": (L, B, R, T),
                        "fontsize0": txt.get_fontsize(),
                        "text_w0": max(1.0, tbbox.width),
                        "text_h0": max(1.0, tbbox.height),
                    })
                    canvas.setCursor(_edge_cursor(edge))
                    return
                if _inside(L, B, R, T, event.x, event.y):
                    drag_state.update({
                        "obj": obj, "mode": "move",
                        "press_px": (event.x, event.y),
                        "patch_xy0": (patch.get_x(), patch.get_y()),
                        "txt_pos0": txt.get_position(),
                    })
                    canvas.setCursor(Qt.ClosedHandCursor)
                    return

        def on_motion(event):
            if drag_state["obj"] is None:
                return
            obj   = drag_state["obj"]
            patch = obj['patch']
            txt   = obj['text']
            press_px, press_py = drag_state["press_px"]
            dx = event.x - press_px   # right = +
            dy = event.y - press_py   # up    = +

            if drag_state["mode"] == "move":
                try:
                    d0 = _px_to_data(press_px, press_py)
                    d1 = _px_to_data(event.x, event.y)
                    ddx, ddy = d1[0] - d0[0], d1[1] - d0[1]
                    px0, py0 = drag_state["patch_xy0"]
                    tx0, ty0 = drag_state["txt_pos0"]
                    patch.set_x(px0 + ddx)
                    patch.set_y(py0 + ddy)
                    txt.set_position((tx0 + ddx, ty0 + ddy))
                except Exception:
                    pass

            elif drag_state["mode"] == "resize":
                L0, B0, R0, T0 = drag_state["bbox0_px"]
                edge = drag_state["edge"]

                if   edge == "right":     nL,nB,nR,nT = L0,    B0,    R0+dx, T0
                elif edge == "left":      nL,nB,nR,nT = L0+dx, B0,    R0,    T0
                elif edge == "top":       nL,nB,nR,nT = L0,    B0,    R0,    T0+dy
                elif edge == "bottom":    nL,nB,nR,nT = L0,    B0+dy, R0,    T0
                elif edge == "top_right": nL,nB,nR,nT = L0,    B0,    R0+dx, T0+dy
                elif edge == "top_left":  nL,nB,nR,nT = L0+dx, B0,    R0,    T0+dy
                elif edge == "bot_right": nL,nB,nR,nT = L0,    B0+dy, R0+dx, T0
                elif edge == "bot_left":  nL,nB,nR,nT = L0+dx, B0+dy, R0,    T0
                else: return

                if nR - nL < MIN_W_PX:
                    if 'left' in edge: nL = nR - MIN_W_PX
                    else:              nR = nL + MIN_W_PX
                if nT - nB < MIN_H_PX:
                    if 'bot' in edge or edge == 'bottom': nB = nT - MIN_H_PX
                    else:                                  nT = nB + MIN_H_PX

                try:
                    d_lb = _px_to_data(nL, nB)
                    d_rt = _px_to_data(nR, nT)
                    patch.set_x(d_lb[0]); patch.set_y(d_lb[1])
                    patch.set_width(max(1e-9,  d_rt[0] - d_lb[0]))
                    patch.set_height(max(1e-9, d_rt[1] - d_lb[1]))
                    txt.set_position(((d_lb[0]+d_rt[0])/2, (d_lb[1]+d_rt[1])/2))
                    PAD_PX = 8
                    avail_w = max(1.0, (nR - nL) - 2*PAD_PX)
                    avail_h = max(1.0, (nT - nB) - 2*PAD_PX)
                    fs_w = drag_state["fontsize0"] * (avail_w / drag_state["text_w0"])
                    fs_h = drag_state["fontsize0"] * (avail_h / drag_state["text_h0"])
                    txt.set_fontsize(max(4, min(fs_w, fs_h)))
                except Exception:
                    pass

            canvas.draw_idle()

        def on_release(event):
            drag_state.update({
                "obj": None, "mode": None, "press_px": None,
                "edge": None, "bbox0_px": None,
                "fontsize0": None, "text_w0": None, "text_h0": None,
                "patch_xy0": None, "txt_pos0": None,
            })
            canvas.setCursor(Qt.ArrowCursor)
            canvas.draw_idle()

        canvas.mpl_connect('motion_notify_event', on_move_hover)
        canvas.mpl_connect('button_press_event', on_press)
        canvas.mpl_connect('motion_notify_event', on_motion)
        canvas.mpl_connect('button_release_event', on_release)

        return preview_widget

    def _prepare_figure_for_export(self, dpi=300, size_inches=(10, 8)):
        """
        Prepare a copy of the figure for export.
        Draw markers if any, otherwise export the graph cleanly.
        """
        import copy
        fig_copy = copy.deepcopy(self.figure)
        fig_copy.set_dpi(dpi)
        fig_copy.set_size_inches(*size_inches)

        # Remove small axes (sliders, colorbars)
        axes_to_remove = [ax for ax in fig_copy.axes
                        if ax.get_position().height < 0.1 or ax.get_position().width < 0.1]
        for ax in axes_to_remove:
            fig_copy.delaxes(ax)

        # Detect active markers and unit
        gc_settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
            Path(__file__).resolve()
        )

        if self.figure == getattr(self.parent_window, 'fig_left', None):
            active_markers = [
                (getattr(self.parent_window, 'cursor_left', None), 1, self.show_markers_left[0]),
                (getattr(self.parent_window, 'cursor_left_2', None), 2, self.show_markers_left[1])
            ]
            unit = gc_settings.value("Graphic1/db_times", "dB")
            graph = gc_settings.value("Tab1/GraphType1", "Magnitude")
            color = 'red'
        elif self.figure == getattr(self.parent_window, 'fig_right', None):
            active_markers = [
                (getattr(self.parent_window, 'cursor_right', None), 1, self.show_markers_right[0]),
                (getattr(self.parent_window, 'cursor_right_2', None), 2, self.show_markers_right[1])
            ]
            unit = gc_settings.value("Graphic2/db_times", "dB")
            graph = gc_settings.value("Tab2/GraphType2", "Magnitude")
            color = 'blue'
        else:
            return fig_copy

        # Keep only visible markers
        active_markers = [(cursor, mid) for cursor, mid, show in active_markers if show and cursor is not None]

        axes_to_use = [ax for ax in fig_copy.axes if ax.get_position().height > 0.1 and ax.get_position().width > 0.1]
        if axes_to_use and active_markers:
            ax = axes_to_use[0]
            for cursor, marker_id in active_markers:
                x_data, y_data = cursor.get_data()
                if len(x_data) == 0 or len(y_data) == 0:
                    continue

                freq = x_data[0]
                magnitude = y_data[0]

                if graph == "Magnitude":
                    if unit == "dB":
                        text = f"Marker {marker_id}\nFreq: {freq:.2f} MHz\n|S|: {magnitude:.3f} dB"
                    else:
                        text = f"Marker {marker_id}\nFreq: {freq:.2f} MHz\n|S|: {magnitude:.3f}"
                elif graph == "Phase":
                    text = f"Marker {marker_id}\nFreq: {freq:.2f} MHz\nPhase: {magnitude:.3f}°"
                else:
                    text = f"Marker {marker_id}\nFreq: {freq:.2f} MHz"

                ax.annotate(
                    text,
                    xy=(freq, magnitude),
                    xycoords='data',
                    fontsize=9,
                    linespacing=2.0,
                    ha='center', va='center',
                    color=color,
                    zorder=10, clip_on=False,
                    bbox=dict(
                        facecolor='white', edgecolor=color,
                        alpha=0.85, boxstyle='square,pad=0.4'
                    )
                )

        return fig_copy

    def copy_to_clipboard(self):
        """Copy the graph image to clipboard preserving all colors and styles."""
        try:
            # Use helper method to prepare figure with high DPI for clipboard
            fig_copy = self._prepare_figure_for_export(dpi=300, size_inches=(10, 8))

            # Generate HIGH RESOLUTION capture preserving all original styling
            buf_clipboard = io.BytesIO()

            fig_copy.subplots_adjust(right=0.85)

            fig_copy.savefig(buf_clipboard,
                           format='png',
                           dpi=300,  # Force high DPI
                           edgecolor='none')
            buf_clipboard.seek(0)

            # Clean up the temporary figure
            plt.close(fig_copy)

            # Create QPixmap from the high-resolution data
            pixmap = QPixmap()
            if pixmap.loadFromData(buf_clipboard.getvalue()):
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setPixmap(pixmap)

                QMessageBox.information(self, "Copy",
                    f"Graph copied to clipboard!")
            else:
                QMessageBox.warning(self, "Copy Error", "Failed to create image.")

        except Exception as e:
            import traceback
            print(f"Clipboard error: {e}")
            print(traceback.format_exc())
            QMessageBox.critical(self, "Copy Error", f"Failed to copy image to clipboard: {str(e)}")

    def save_as_image(self):
        """Save the graph exactly as shown in preview."""
        if not hasattr(self, 'preview_canvas') or self.preview_canvas is None:
            QMessageBox.warning(self, "Save Error", "No preview available.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Graph as Image", "graph.png",
            "PNG Files (*.png);;JPG Files (*.jpg);;PDF Files (*.pdf);;SVG Files (*.svg)"
        )
        if not file_path:
            return

        try:
            self.preview_canvas.figure.savefig(file_path, dpi=300)
            QMessageBox.information(self, "Save", f"Graph saved as: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save image: {str(e)}")


    def save_as_csv(self):
        """Save the graph data as CSV."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Graph Data as CSV",
                "graph_data.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return  # Usuario canceló

            for i, ax in enumerate(self.figure.axes):
                print(f"\n=== Axis {i} ===")
                print(f"Title: {ax.get_title()}")
                print(f"Number of lines: {len(ax.lines)}")

                for j, line in enumerate(ax.lines):
                    print(f"  Line {j}: visible={line.get_visible()}")
                    print(f"    X data sample: {line.get_xdata()[:5]}")
                    print(f"    Y data sample: {line.get_ydata()[:5]}")
                    print(f"    Has attribute 'freqs'? {'freqs' in dir(line)}")
            csv_data = []
            headers = []

            for ax in self.figure.axes:
                # Ignorar ejes de sliders o muy pequeños
                if hasattr(ax, 'get_position'):
                    pos = ax.get_position()
                    if pos.height < 0.1 or pos.width < 0.1:
                        continue

                if self.left_graph == "Smith Diagram" or self.right_grap == "Smith Diagram":
                    if self.freqs is None:
                        QMessageBox.warning(self, "Save Error", "Frequency data is missing for Smith Diagram!")
                        return

                    headers = ['Frequency (Hz)', 'Re', 'Im']
                    csv_data = []

                    # Recorremos todas las líneas visibles y tomamos X=Re, Y=Im
                    for ax in self.figure.axes:
                        for line in ax.lines:
                            if line.get_visible():
                                x_data_re = line.get_xdata()   # parte real
                                y_data_im = line.get_ydata()   # parte imaginaria

                                # Zip con self.freqs
                                for f, re, im in zip(self.freqs, x_data_re, y_data_im):
                                    csv_data.append([f, re, im])
                else:
                    for i, line in enumerate(ax.lines):
                        if line.get_visible() and len(line.get_xdata()) > 1:
                            x_data = line.get_xdata()
                            y_data = line.get_ydata()
                            # Convert MHz a Hz
                            x_data_hz = [x * 1e6 for x in x_data]

                            if not headers:
                                headers = ['Freq (Hz)', 'Y']
                                csv_data = [[x, y] for x, y in zip(x_data_hz, y_data)]
                            else:
                                headers.extend([f'Freq_{i+1} (Hz)', f'Y_{i+1}'])
                                for j, (x, y) in enumerate(zip(x_data_hz, y_data)):
                                    if j < len(csv_data):
                                        csv_data[j].extend([x, y])

            # Depuración: imprimir el contenido
            print("CSV Headers:", headers)
            print("CSV Data Sample:", csv_data[:5])  # primeros 5 registros

            # Guardar CSV
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(csv_data)

            QMessageBox.information(self, "Save", f"Graph data saved as: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save CSV: {str(e)}")
            print("Exception:", e)
