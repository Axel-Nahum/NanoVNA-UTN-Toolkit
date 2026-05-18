import logging

from PySide6.QtWidgets import (
    QApplication, QMessageBox
)

from NanoVNA_UTN_Toolkit.modules.dut_measurement.exporters.export.export_dialog import ExportDialog

# ------------------------------------------------------------------------------------------------------------------ #

def open_export_dialog(self, event):
    """Open the export dialog for the clicked graph."""
    # Determine which graph was clicked based on event position
    widget_under_cursor = QApplication.widgetAt(event.globalPos())
    
    try:
        # Default to left figure
        figure_to_export = self.fig_left
        panel_name = "Left Panel"
        
        # Try to determine which canvas was clicked
        if hasattr(self, 'canvas_right') and widget_under_cursor:
            # Walk up the widget hierarchy to find the canvas
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == self.canvas_right:
                    figure_to_export = self.fig_right
                    panel_name = "Right Panel"
                    break
                elif current_widget == self.canvas_left:
                    figure_to_export = self.fig_left
                    panel_name = "Left Panel"
                    break
                current_widget = current_widget.parent()

        # Close previous export dialog if it exists
        if hasattr(self, 'export_dialog') and self.export_dialog is not None:
            self.export_dialog.close()
            self.export_dialog.deleteLater()
            self.export_dialog = None

        # Create and show new export dialog
        show_left_markers = [self.show_graphic1_marker1, self.show_graphic1_marker2]
        show_right_markers = [self.show_graphic2_marker1, self.show_graphic2_marker2]

        update_cursor_left = [self.update_cursor, self.update_cursor_2]
        update_cursor_right = [self.update_right_cursor, self.update_right_cursor_2]

        self.export_dialog = ExportDialog(
            self,
            figure_to_export,
            left_graph=self.left_graph_type,
            right_graph=self.right_graph_type,
            freqs=self.freqs,
            show_markers_left = show_left_markers,
            show_markers_right = show_right_markers,
            update_cursor_left = update_cursor_left,
            update_cursor_right = update_cursor_right
        )

        self.export_dialog.setWindowTitle(f"NanoVNA UTN Toolkit - Export Graph - {panel_name}")
        self.export_dialog.exec()
        
    except Exception as e:
        logging.error(f"Error opening export dialog: {e}")
        QMessageBox.warning(self, "Export Error", f"Failed to open export dialog: {str(e)}")