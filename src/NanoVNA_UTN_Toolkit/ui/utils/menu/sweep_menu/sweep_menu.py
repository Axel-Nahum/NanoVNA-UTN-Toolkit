import logging

def open_sweep_options(self):
    from NanoVNA_UTN_Toolkit.ui.sweep_window import SweepOptionsWindow

    # Log sweep options opening
    logging.info("[graphics_window.open_sweep_options] Opening sweep options window")

    # Try to get the current VNA device (this is a placeholder for now)
    vna_device = self.get_current_vna_device()

    # Log device information being passed to sweep options
    if vna_device:
        device_type = type(vna_device).__name__
        logging.info(f"[graphics_window.open_sweep_options] Device found: {device_type}")
        if hasattr(vna_device, 'sweep_points_min') and hasattr(vna_device, 'sweep_points_max'):
            logging.info(f"[graphics_window.open_sweep_options] Device sweep limits: {vna_device.sweep_points_min} to {vna_device.sweep_points_max}")
        else:
            logging.info("[graphics_window.open_sweep_options] Device has no sweep_points limits")
    else:
        logging.warning("[graphics_window.open_sweep_options] No VNA device available - using default limits")

    if hasattr(self, 'sweep_options_window') and self.sweep_options_window is not None:
        self.sweep_options_window.close()
        self.sweep_options_window.deleteLater()
        self.sweep_options_window = None

    logging.info("[graphics_window.open_sweep_options] Creating new sweep options window")
    self.sweep_options_window = SweepOptionsWindow(parent=self, vna_device=self.vna_device)

    self.sweep_options_window.show()
    self.sweep_options_window.raise_()
    self.sweep_options_window.activateWindow()