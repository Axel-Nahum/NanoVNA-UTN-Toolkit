import logging
import skrf as rf

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMenu
)

# Import get_settings 

try:
    from NanoVNA_UTN_Toolkit.shared.utils.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.view_edit_menu.view_edit_menu import open_view
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.set_range.set_range import show_y_range_dialog
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.toggle_db_times.toggle_db_times import toggle_db_times
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.export_dialog.open_export_dialog import open_export_dialog
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility import toggle_marker_visibility, toggle_marker2_visibility
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# -------------------------------------------------------------------------------------------------------------------- #

def handle_contextMenuEvent(self, event):
    menu = QMenu(self)

    view_menu = menu.addAction("View")

    menu.addSeparator()
    
    marker1_graphic1_action = menu.addAction("Marker 1 - Graphic 1")
    marker1_graphic1_action.setCheckable(True)
    marker1_graphic1_action.setChecked(self.show_graphic1_marker1)

    marker1_graphic2_action = menu.addAction("Marker 1 - Graphic 2")
    marker1_graphic2_action.setCheckable(True)
    marker1_graphic2_action.setChecked(self.show_graphic2_marker1)

    marker2_graphic1_action = menu.addAction("Marker 2 -Graphic 1")
    marker2_graphic1_action.setCheckable(True)
    marker2_graphic1_action.setChecked(False)
    marker2_graphic1_action.setChecked(self.show_graphic1_marker2)

    marker2_graphic2_action = menu.addAction("Marker 2 -Graphic 2")
    marker2_graphic2_action.setCheckable(True)
    marker2_graphic2_action.setChecked(False)
    marker2_graphic2_action.setChecked(self.show_graphic2_marker2)

    # --- Lock markers action ---
    lock_markers_action = menu.addAction("Lock Markers ✓" if self.markers_locked else "Lock Markers")
    lock_markers_action.setCheckable(True)
    lock_markers_action.setChecked(self.markers_locked)

    # --- Determine which graph was clicked ---
    widget_under_cursor = QApplication.widgetAt(event.globalPos())
    graph_number = 1  # default left
    current_widget = widget_under_cursor
    while current_widget:
        if hasattr(self, "canvas_right") and current_widget == self.canvas_right:
            graph_number = 2
            break
        elif hasattr(self, "canvas_left") and current_widget == self.canvas_left:
            graph_number = 1
            break
        current_widget = current_widget.parent()

    # --- Read the current unit from INI ---
    import os
    from PySide6.QtCore import QSettings

    # Load configuration for graphics settings and visualization parameters
    settings = get_settings(
        "INI/dut_measurement/graphics_config/graphics_config.ini",
        "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
        Path(__file__).resolve()
    )

    ini_section = "Graphic1" if graph_number == 1 else "Graphic2"

    tab_section = "Tab1" if graph_number == 1 else "Tab2"

    settings.beginGroup(ini_section)
    current_unit = settings.value("db_times", "dB")
    settings.endGroup()

    settings.beginGroup(tab_section)
    s_param = settings.value("SParameter", "S11")
    graph_type = settings.value("GraphType1" if graph_number == 1 else "GraphType2", "Smith Diagram")
    settings.endGroup()

    # Check if current graph is Smith Diagram
    is_smith_diagram = graph_type == "Smith Diagram"

    # --- Unit submenu (disabled for Smith Diagram) ---
    menu.addSeparator()
    unit_menu = QMenu(f"Unit", self)
    unit_menu.setEnabled(not is_smith_diagram)
    
    # Initialize unit actions as None
    voltage_action = None
    db_action = None
    
    if current_unit == "dB":
        voltage_action = unit_menu.addAction(f"Times ({s_param})")
    else:
        db_action = unit_menu.addAction(f"dB({s_param})")
    menu.addMenu(unit_menu)

    # ---- grid ----

    menu.addSeparator()

    # --- Grid action ---
    widget_under_cursor = QApplication.widgetAt(event.globalPos())
    target_ax = None
    target_fig = None
    target_attr = None

    current_widget = widget_under_cursor
    while current_widget:
        if hasattr(self, "canvas_right") and current_widget == self.canvas_right:
            target_ax = self.ax_right
            target_fig = self.fig_right
            target_attr = "grid_enabled_right"
            selected_graph_name = "right"
            break
        elif hasattr(self, "canvas_left") and current_widget == self.canvas_left:
            target_ax = self.ax_left
            target_fig = self.fig_left
            target_attr = "grid_enabled_left"
            selected_graph_name = "left"
            break
        current_widget = current_widget.parent()

    current_state = getattr(self, target_attr, True) if target_attr else True
    if target_attr is not None:
        setattr(self, target_attr, current_state)

    if target_ax and target_fig:
        target_ax.grid(current_state)
        target_fig.canvas.draw_idle()

    # --- Grid action (disabled for Smith Diagram) ---
    grid_action = menu.addAction("Grid ✓" if current_state else "Grid")
    grid_action.setCheckable(True)
    grid_action.setChecked(current_state)
    grid_action.setEnabled(not is_smith_diagram)

    # --- Range action (disabled for Smith Diagram) ---
    range_action = menu.addAction("Set range")
    range_action.setEnabled(not is_smith_diagram)

    smith_action = None

    #smith_action = menu.addAction("Smith Normalized")

    # --- Export ---
    menu.addSeparator()
    export_action = menu.addAction("Export...")

    selected_action = menu.exec(event.globalPos())

    self.ax_to_network = {
        self.ax_left: rf.Network(frequency=self.freqs, s=self.s11, z0=50),
        self.ax_right: rf.Network(frequency=self.freqs, s=self.s11, z0=50)
    }

    # --- Handle actions ---
    if selected_action == view_menu:
        open_view(self)

    # --- Markers ---

    elif selected_action == marker1_graphic1_action:
        self.show_graphic1_marker1 = not self.show_graphic1_marker1
        toggle_marker_visibility(self, 0, self.show_graphic1_marker1)

        if self.show_graphic1_marker1:
            self.info_panel_left.show()
        if not self.show_graphic1_marker1 and self.show_graphic1_marker2:
            self.info_panel_left.hide()

        if self.show_graphic1_marker1 and not self.show_graphic1_marker2:
            self.info_panel_left.show()
            self.info_panel_left_2.hide()

    elif selected_action == marker1_graphic2_action:
        self.show_graphic2_marker1 = not self.show_graphic2_marker1
        toggle_marker_visibility(self, 1, self.show_graphic2_marker1)

        if self.show_graphic2_marker1:
            self.info_panel_right.show()
        if not self.show_graphic2_marker1 and self.show_graphic2_marker2:
            self.info_panel_right.hide()
        if self.show_graphic2_marker1 and not self.show_graphic2_marker2:
            self.info_panel_right.show()
            self.info_panel_right_2.hide()

    elif selected_action == marker2_graphic1_action:
        self.show_graphic1_marker2 = not self.show_graphic1_marker2
        
        toggle_marker2_visibility(self, 0, self.show_graphic1_marker2)

        if self.show_graphic1_marker2:
            self.info_panel_left_2.show()
        if not self.show_graphic1_marker2 and self.show_graphic1_marker1:
            self.info_panel_left_2.hide()
        if self.show_graphic1_marker2 and not self.show_graphic1_marker1:
            self.info_panel_left.hide()
            self.info_panel_left_2.show()

    elif selected_action == marker2_graphic2_action:
        self.show_graphic2_marker2 = not self.show_graphic2_marker2
        
        toggle_marker2_visibility(self, 1, self.show_graphic2_marker2)

        if self.show_graphic2_marker2:
            self.info_panel_right_2.show()
        if not self.show_graphic2_marker2 and self.show_graphic2_marker1:
            self.info_panel_right_2.hide()
        if not self.show_graphic2_marker1 and self.show_graphic2_marker2:
            self.info_panel_right.hide()
            self.info_panel_right_2.show()

    # --- Lock Markers ---

    elif selected_action == lock_markers_action:
        self.markers_locked = not self.markers_locked

        lock_markers_action.setChecked(self.markers_locked)

        settings.setValue("Markers/locked", self.markers_locked)
        
        if self.markers_locked:
            val = self.slider_left.val
            self.slider_right.set_val(val)
            self.update_right_cursor(val)

            val_2 = self.slider_left_2.val
            self.slider_right_2.set_val(val_2)
            self.update_right_cursor_2(val_2)

    # --- Grid ---
        
    elif selected_action == grid_action and target_ax and target_fig and target_attr and not is_smith_diagram:
        new_state = not getattr(self, target_attr, True)
        if target_attr is not None:
            setattr(self, target_attr, new_state)
        target_ax.grid(new_state)
        target_fig.canvas.draw_idle()
        grid_action.setText("Grid ✓" if new_state else "Grid")

    # --- Range ---

    elif selected_action == range_action and not is_smith_diagram:
        show_y_range_dialog(self, target_ax)

    # --- Smith Normalized ---
        
    # --- Toggle Smith Normalized ---
    elif smith_action is not None and selected_action == smith_action and target_ax and target_fig:
        # Determinar si el gráfico seleccionado es tipo Smith

        logging.info(f"selected_graph_name: {selected_graph_name}")
        logging.info(f"left_graph_type: {self.left_graph_type}")
        logging.info(f"right_graph_type: {self.right_graph_type}")
        logging.info(f"target_ax: {target_ax}")
        logging.info(f"target_fig: {target_fig}")

        is_smith = (selected_graph_name == "left" and self.left_graph_type.lower() == "smith diagram") or \
                (selected_graph_name == "right" and self.right_graph_type.lower() == "smith diagram")

        if not is_smith:
            # Mostrar advertencia al usuario
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Smith Normalized",
                                    "The selected graph is not a Smith chart and cannot be normalized to Γ.")
            return

        # Tomar el Network asociado al ax
        net = self.ax_to_network.get(target_ax, None)
        if net is None:
            return

        # Dibujar Gamma normalizado
        gamma = net.s[:,0,0]
        target_ax.clear()
        target_ax.plot(gamma.real, gamma.imag, 'o-')
        target_ax.set_xlim(-1, 1)
        target_ax.set_ylim(-1, 1)
        target_ax.set_xlabel("Re(Γ)")
        target_ax.set_ylabel("Im(Γ)")
        target_ax.grid(True)
        target_fig.canvas.draw_idle()

    # --- Export ---

    elif selected_action == export_action:
        open_export_dialog(self, event)

    # --- Handle unit change (disabled for Smith Diagram) ---
    elif current_unit == "dB" and not is_smith_diagram:
        if selected_action == voltage_action:
            toggle_db_times(self, event, "Voltage ratio")
    elif current_unit in ("Power ratio", "Voltage ratio") and not is_smith_diagram:
        if selected_action == db_action:
            toggle_db_times(self, event, "dB")

    if self.show_graphic1_marker1 and self.show_graphic1_marker2 or self.show_graphic2_marker1 and self.show_graphic2_marker2:
        self.markers_button.show()
    else:
        self.markers_button.hide()