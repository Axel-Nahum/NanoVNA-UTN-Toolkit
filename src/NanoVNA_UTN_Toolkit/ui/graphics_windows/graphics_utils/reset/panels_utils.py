import logging
import sys

# Import load graph configuration

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.load_graph_config.load_graph_config import load_graph_configuration
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

from PySide6.QtCore import QTimer

# ------------------------------------------------------------------------------------------------------------------- #

def _clear_axis_and_show_message(self, panel_side='right', message_pos=(0.5, 0.5)):
    """Clear axis and show waiting message for a specific panel."""
    
    if panel_side == 'right':
        if hasattr(self, 'ax_right') and self.ax_right:
            self.ax_right.text(
                message_pos[0], message_pos[1],
                r"$\mathrm{Waiting\ for\ sweep\ data\ ...}$",
                transform=self.ax_right.transAxes,
                ha='center', va='center',
                fontsize=15, color='white'
            )

            for line in self.ax_right.lines:
                line.remove()

            self.ax_right.grid(False)

        if hasattr(self, 'canvas_right') and self.canvas_right:
            self.canvas_right.draw()

    elif panel_side == 'left':
        if hasattr(self, 'ax_left') and self.ax_left:
            self.ax_left.text(
                message_pos[0], message_pos[1],
                r"$\mathrm{Waiting\ for\ sweep\ data\ ...}$",
                transform=self.ax_left.transAxes,
                ha='center', va='center',
                fontsize=15, color='white'
            )

            for line in self.ax_left.lines:
                line.remove()

            self.ax_left.grid(False)

        if hasattr(self, 'canvas_left') and self.canvas_left:
            self.canvas_left.draw()

def _clear_panel_labels(self, panel_side='left'):
    """Clear all labels for a specific panel (left or right)."""
    if panel_side == 'left' and hasattr(self, 'labels_left') and self.labels_left:
        # Clear left panel marker 1 labels
        if "freq" in self.labels_left:
            self.labels_left["freq"].setText("--")
            QTimer.singleShot(0, lambda: self.labels_left["freq"].setSelection(0, 0))
        if "val" in self.labels_left:
            self.labels_left["val"].setText(f"{self.left_s_param}: -- + j--")
        if "mag" in self.labels_left:
            self.labels_left["mag"].setText(f"|{self.left_s_param}|: --")
        if "phase" in self.labels_left:
            self.labels_left["phase"].setText("Phase: --")
        if "z" in self.labels_left:
            self.labels_left["z"].setText("Zin (Z0): -- + j--")
        if "il" in self.labels_left:
            self.labels_left["il"].setText("IL: --")
        if "vswr" in self.labels_left:
            self.labels_left["vswr"].setText("VSWR: --")
        # Clear focus from frequency field
        if "freq" in self.labels_left:
            try:
                self.labels_left["freq"].deselect()
                self.labels_left["freq"].clearFocus()
            except Exception:
                pass  # Ignore if widget doesn't have these methods

    elif panel_side == 'right' and hasattr(self, 'labels_right') and self.labels_right:
        # Clear right panel marker 1 labels
        if "freq" in self.labels_right:
            self.labels_right["freq"].setText("--")
        if "val" in self.labels_right:
            self.labels_right["val"].setText(f"{self.right_s_param}: -- + j--")
        if "mag" in self.labels_right:
            self.labels_right["mag"].setText(f"|{self.right_s_param}|: --")
        if "phase" in self.labels_right:
            self.labels_right["phase"].setText("Phase: --")
        if "z" in self.labels_right:
            self.labels_right["z"].setText("Zin (Z0): -- + j--")
        if "il" in self.labels_right:
            self.labels_right["il"].setText("IL: --")
        if "vswr" in self.labels_right:
            self.labels_right["vswr"].setText("VSWR: --")
        # Clear focus from frequency field
        if "freq" in self.labels_right:
            try:
                self.labels_right["freq"].deselect()
                self.labels_right["freq"].clearFocus()
            except Exception:
                pass  # Ignore if widget doesn't have these methods

    if panel_side == 'left' and hasattr(self, 'labels_left_2') and self.labels_left_2:
        # Clear left panel marker 2 labels
        if "freq" in self.labels_left_2:
            self.labels_left_2["freq"].setText("--")
        if "val" in self.labels_left_2:
            self.labels_left_2["val"].setText(f"{self.left_s_param}: -- + j--")
        if "mag" in self.labels_left_2:
            self.labels_left_2["mag"].setText(f"|{self.left_s_param}|: --")
        if "phase" in self.labels_left_2:
            self.labels_left_2["phase"].setText("Phase: --")
        if "z" in self.labels_left_2:
            self.labels_left_2["z"].setText("Zin (Z0): -- + j--")
        if "il" in self.labels_left_2:
            self.labels_left_2["il"].setText("IL: --")
        if "vswr" in self.labels_left_2:
            self.labels_left_2["vswr"].setText("VSWR: --")
        # Clear focus from frequency field
        if "freq" in self.labels_left_2:
            try:
                self.labels_left_2["freq"].deselect()
                self.labels_left_2["freq"].clearFocus()
            except Exception:
                pass  # Ignore if widget doesn't have these methods
            
    elif panel_side == 'right' and hasattr(self, 'labels_right_2') and self.labels_right_2:
        # Clear right panel marker 2 labels
        if "freq" in self.labels_right_2:
            self.labels_right_2["freq"].setText("--")
        if "val" in self.labels_right_2:
            self.labels_right_2["val"].setText(f"{self.right_s_param}: -- + j--")
        if "mag" in self.labels_right_2:
            self.labels_right_2["mag"].setText(f"|{self.right_s_param}|: --")
        if "phase" in self.labels_right_2:
            self.labels_right_2["phase"].setText("Phase: --")
        if "z" in self.labels_right_2:
            self.labels_right_2["z"].setText("Zin (Z0): -- + j--")
        if "il" in self.labels_right_2:
            self.labels_right_2["il"].setText("IL: --")
        if "vswr" in self.labels_right_2:
            self.labels_right_2["vswr"].setText("VSWR: --")
        # Clear focus from frequency field
        if "freq" in self.labels_right_2:
            try:
                self.labels_right_2["freq"].deselect()
                self.labels_right_2["freq"].clearFocus()
            except Exception:
                pass  # Ignore if widget doesn't have these methods
            
        self.labels_right_2.get("phase")
        self.labels_right_2["phase"].setText("Phase: --")
        self.labels_right_2.get("z")
        self.labels_right_2["z"].setText("Zin (Z0): -- + j--")
        self.labels_right_2.get("il")
        self.labels_right_2["il"].setText("IL: --")
        self.labels_right_2.get("vswr")
        self.labels_right_2["vswr"].setText("VSWR: --")

def _clear_marker_fields_only(self):
    """Clear only marker information fields without affecting the graphs."""
    logging.info("[graphics_window._clear_marker_fields_only] Clearing marker information fields only")
    
    # --- Clear left panel marker information ---
    if hasattr(self, 'labels_left') and self.labels_left:
        freq_left = self.labels_left.get("freq")
        if freq_left:
            freq_left.setText("--")
            freq_left.setSelection(0, 0)  
            freq_left.setCursorPosition(0) 
            freq_left.deselect()
            freq_left.clearFocus()
        self.labels_left.get("val") and self.labels_left["val"].setText("S11: -- + j--")
        self.labels_left.get("mag") and self.labels_left["mag"].setText("|S11|: --")
        self.labels_left.get("phase") and self.labels_left["phase"].setText("Phase: --")
        self.labels_left.get("z") and self.labels_left["z"].setText("Zin (Z0): -- + j--")
        self.labels_left.get("il") and self.labels_left["il"].setText("IL: --")
        self.labels_left.get("vswr") and self.labels_left["vswr"].setText("VSWR: --")

    # --- Clear right panel marker information ---
    if hasattr(self, 'labels_right') and self.labels_right:
        freq_right = self.labels_right.get("freq")
        if freq_right:
            freq_right.setText("--")   # set "--"
            freq_right.setSelection(0, 0)  
            freq_right.setCursorPosition(0) 
            freq_right.deselect()
            freq_right.clearFocus()
        self.labels_right.get("val") and self.labels_right["val"].setText("S21: -- + j--")
        self.labels_right.get("mag") and self.labels_right["mag"].setText("|S21|: --")
        self.labels_right.get("phase") and self.labels_right["phase"].setText("Phase: --")
        self.labels_right.get("z") and self.labels_right["z"].setText("Zin (Z0): -- + j--")
        self.labels_right.get("il") and self.labels_right["il"].setText("IL: --")
        self.labels_right.get("vswr") and self.labels_right["vswr"].setText("VSWR: --")

    # --- Clear left panel marker information ---
    if hasattr(self, 'labels_left_2') and self.labels_left_2:
        freq_left = self.labels_left_2.get("freq")
        if freq_left:
            freq_left.setText("--")    # set "--"
            freq_left.deselect()       # remove selection
            freq_left.clearFocus()     # remove focus so it's not blue
        self.labels_left_2.get("val") and self.labels_left_2["val"].setText("S11: -- + j--")
        self.labels_left_2.get("mag") and self.labels_left_2["mag"].setText("|S11|: --")
        self.labels_left_2.get("phase") and self.labels_left_2["phase"].setText("Phase: --")
        self.labels_left_2.get("z") and self.labels_left_2["z"].setText("Zin (Z0): -- + j--")
        self.labels_left_2.get("il") and self.labels_left_2["il"].setText("IL: --")
        self.labels_left_2.get("vswr") and self.labels_left_2["vswr"].setText("VSWR: --")

    # --- Clear right panel marker information ---
    if hasattr(self, 'labels_right_2') and self.labels_right_2:
        freq_right = self.labels_right_2.get("freq")
        if freq_right:
            freq_right.setText("--")   # set "--"
            freq_right.deselect()      # remove selection
            freq_right.clearFocus()    # remove focus so it's not blue
        self.labels_right_2.get("val") and self.labels_right_2["val"].setText("S21: -- + j--")
        self.labels_right_2.get("mag") and self.labels_right_2["mag"].setText("|S21|: --")
        self.labels_right_2.get("phase") and self.labels_right_2["phase"].setText("Phase: --")
        self.labels_right_2.get("z") and self.labels_right_2["z"].setText("Zin (Z0): -- + j--")
        self.labels_right_2.get("il") and self.labels_right_2["il"].setText("IL: --")
        self.labels_right_2.get("vswr") and self.labels_right_2["vswr"].setText("VSWR: --")

    # Do NOT clear the graphs - leave them with the actual data
    logging.info("[graphics_window._clear_marker_fields_only] Marker fields cleared, graphs preserved")

def _clear_all_marker_fields(self):
    """Clear marker values but keep all panels and labels intact."""

    logging.info("[graphics_window._clear_all_marker_fields] Clearing marker values but keeping layout intact")

    config = load_graph_configuration()
    graph_type_tab1 = config['graph_type_tab1']
    graph_type_tab2 = config['graph_type_tab2']

    if graph_type_tab1 == "Smith Diagram":

        # Left panel
        _clear_panel_labels(self, 'left')

        # Hide cursors
        if hasattr(self, 'cursor_left') and self.cursor_left:
            self.cursor_left.set_visible(False)

        if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
            self.cursor_left_2.set_visible(False)
        
        _clear_axis_and_show_message(self, 'left', (0.5, -0.1))

    if graph_type_tab2 == "Smith Diagram":

        # Right panel
        _clear_panel_labels(self, 'right')

        if hasattr(self, 'cursor_right') and self.cursor_right:
            self.cursor_right.set_visible(False)
        
        if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
            self.cursor_right_2.set_visible(False)

        _clear_axis_and_show_message(self, 'right', (0.5, -0.1))

    if graph_type_tab1 == "Magnitude" or graph_type_tab1 == "Phase":
        # Left panel
        _clear_panel_labels(self, 'left')

        # Hide cursors
        if hasattr(self, 'cursor_left') and self.cursor_left:
            self.cursor_left.set_visible(False)

        # Hide cursors
        if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
            self.cursor_left_2.set_visible(False)

        _clear_axis_and_show_message(self, 'left', (0.5, 0.5))


    if graph_type_tab2 == "Magnitude" or graph_type_tab2 == "Phase":

        # Right panel
        _clear_panel_labels(self, 'right')

        if hasattr(self, 'cursor_right_2') and self.cursor_right:
            self.cursor_right.set_visible(False)

        if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
            self.cursor_right_2.set_visible(False)

        _clear_axis_and_show_message(self, 'right', (0.5, 0.5))
