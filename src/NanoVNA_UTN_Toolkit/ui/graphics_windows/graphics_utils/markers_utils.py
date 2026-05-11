import logging
import sys

# Import load graph configuration

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.load_graph_config.load_graph_config import load_graph_configuration
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def _clear_all_marker_fields(self):
        """Clear marker values but keep all panels and labels intact."""
        
        logging.info("[graphics_window._clear_all_marker_fields] Clearing marker values but keeping layout intact")

        config = load_graph_configuration()
        graph_type_tab1 = config['graph_type_tab1']
        graph_type_tab2 = config['graph_type_tab2']

        if graph_type_tab1 == "Smith Diagram":

            # Left panel
            self._clear_panel_labels('left')

            # Hide cursors
            if hasattr(self, 'cursor_left') and self.cursor_left:
                self.cursor_left.set_visible(False)

            if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
                self.cursor_left_2.set_visible(False)
            
            # Clear axes but keep empty plot with message
            if hasattr(self, 'ax_left') and self.ax_left:
                #self.ax_left.clear()
                self.ax_left.text(
                    0.5, -0.1,
                    r"$\mathrm{Waiting\ for\ sweep\ data\ ...}$",
                    transform=self.ax_left.transAxes,
                    ha='center', va='center',
                    fontsize=15, color='white'
                )

                for line in self.ax_left.lines:
                    line.remove()

                self.ax_left.grid(False)

            # Redraw
            if hasattr(self, 'canvas_left') and self.canvas_left:
                self.canvas_left.draw()
           
        if graph_type_tab2 == "Smith Diagram":

            # Right panel
            self._clear_panel_labels('right')

            if hasattr(self, 'cursor_right') and self.cursor_right:
                self.cursor_right.set_visible(False)
            
            if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
                self.cursor_right_2.set_visible(False)

            self._clear_axis_and_show_message('right', (0.5, -0.1))

        if graph_type_tab1 == "Magnitude" or graph_type_tab1 == "Phase":
            # Left panel
            self._clear_panel_labels('left')

            # Hide cursors
            if hasattr(self, 'cursor_left') and self.cursor_left:
                self.cursor_left.set_visible(False)

            # Hide cursors
            if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
                self.cursor_left_2.set_visible(False)

            # Clear axes but keep empty plot with message
            if hasattr(self, 'ax_left') and self.ax_left:
                self.ax_left.text(
                    0.5, 0.5,
                    r"$\mathrm{Waiting\ for\ sweep\ data\ ...}$",
                    transform=self.ax_left.transAxes,
                    ha='center', va='center',
                    fontsize=15, color='white'
                )

                for line in self.ax_left.lines:
                    line.remove()

                self.ax_left.grid(False)

            # Redraw
            if hasattr(self, 'canvas_left') and self.canvas_left:
                self.canvas_left.draw()

        if graph_type_tab2 == "Magnitude" or graph_type_tab2 == "Phase":

            # Right panel
            self._clear_panel_labels('right')

            if hasattr(self, 'cursor_right_2') and self.cursor_right:
                self.cursor_right.set_visible(False)

            if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
                self.cursor_right_2.set_visible(False)

            self._clear_axis_and_show_message('right', (0.5, 0.5))
