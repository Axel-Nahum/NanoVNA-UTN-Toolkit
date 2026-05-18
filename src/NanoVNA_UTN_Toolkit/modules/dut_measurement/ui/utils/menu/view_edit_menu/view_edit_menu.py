import logging

def edit_graphics_markers(self):
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.edit_graphics.edit_graphics_window import EditGraphics
    self.edit_graphics_window = EditGraphics(nano_window=self) 
    self.edit_graphics_window.show()

# =================== VIEW ==================

def open_view(self):
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.view_edit.view_window import View
    
    # Cerrar la instancia anterior si existe
    if hasattr(self, 'view_window') and self.view_window is not None:
        self.view_window.close()
        self.view_window.deleteLater()
        self.view_window = None

    # Crear nueva instancia de View
    self.view_window = View(nano_window=self)
    self.view_window.show()
    self.view_window.raise_()
    self.view_window.activateWindow()