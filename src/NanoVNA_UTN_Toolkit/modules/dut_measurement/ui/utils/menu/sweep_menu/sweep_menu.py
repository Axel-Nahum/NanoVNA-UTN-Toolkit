import logging

def get_current_vna_device(self):
    """Try to get the current VNA device."""
    logging.info("[graphics_window.get_current_vna_device] Searching for current VNA device")
    
    try:
        # Check if we have device stored in this graphics window
        if hasattr(self, 'vna_device') and self.vna_device is not None:
            device_type = type(self.vna_device).__name__
            logging.info(f"[graphics_window.get_current_vna_device] Found stored device: {device_type}")
            return self.vna_device
            
        # Check if we can access the connection window device
        # This is a more advanced implementation for future development
        logging.warning("[graphics_window.get_current_vna_device] No VNA device found in graphics window")
        logging.warning("[graphics_window.get_current_vna_device] Device wasn't passed from previous window")
        
        return None
    except Exception as e:
        logging.error(f"[graphics_window.get_current_vna_device] Error getting current VNA device: {e}")
        return None

def open_sweep_options(self):
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window import SweepOptionsWindow

    # Log sweep options opening
    logging.info("[graphics_window.open_sweep_options] Opening sweep options window")

    # Try to get the current VNA device (this is a placeholder for now)
    vna_device = get_current_vna_device(self)

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