import logging
from PySide6.QtWidgets import QMessageBox

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.sliders_reset import _reset_sliders_after_reconnect
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from src.NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_refresh import run_sweep, update_reconnect_button_state
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def reconnect_device(self):
    """Reconnect to the VNA device."""
    logging.info("[graphics_window.reconnect_device] Manual reconnection requested")
    
    if not self.vna_device:
        # Show error dialog but don't disable the button
        error_msg = ("No VNA device is currently available.\n\n"
                    "Please:\n"
                    "1. Ensure your VNA device is connected via USB\n"
                    "2. Remove and reconnect the device\n"
                    "3. Try clicking Connect again\n\n"
                    "If the problem persists, check USB connection and restart the program.")
        QMessageBox.critical(self, "Device Connection Error", error_msg)
        logging.warning(f"[graphics_window.reconnect_device] No VNA device available")
        return
        
    # Disable reconnect button during reconnection
    self.reconnect_button.setEnabled(False)
    self.reconnect_button.setText("Connecting...")
    # Remove custom styling to use standard disabled button appearance
    self.reconnect_button.setStyleSheet("")
    # Force complete style refresh to clear any persistent styling
    if hasattr(self.reconnect_button, 'style'):
        self.reconnect_button.style().unpolish(self.reconnect_button)
        self.reconnect_button.style().polish(self.reconnect_button)
        self.reconnect_button.update()
    
    # Also disable sweep button during reconnection
    self.sweep_button.setEnabled(False)
    
    try:
        device_type = type(self.vna_device).__name__
        logging.info(f"[graphics_window.reconnect_device] Attempting to reconnect {device_type}")
        
        # If already connected, disconnect first
        if self.vna_device.connected():
            logging.info("[graphics_window.reconnect_device] Device already connected, disconnecting first")
            self.vna_device.disconnect()
            
        # Attempt reconnection
        self.vna_device.connect()
        
        if self.vna_device.connected():
            success_msg = f"Successfully reconnected to {device_type}"
            logging.info(f"[graphics_window.reconnect_device] {success_msg}")
            QMessageBox.information(self, "Connection Successful", success_msg)
            
            # Reset sliders and cursors to initial position after successful reconnection
            _reset_sliders_after_reconnect(self)
            
            # Enable sweep button since device is now connected
            self.sweep_button.setEnabled(True)
        else:
            # Connection failed - show detailed error dialog but keep button enabled
            error_msg = (f"Failed to connect to {device_type}.\n\n"
                        "Please try the following:\n"
                        "1. Remove and reconnect the VNA device\n"
                        "2. Check USB cable and port\n"
                        "3. Ensure device drivers are properly installed\n"
                        "4. Close other software that might be using the device\n"
                        "5. Try clicking Connect again\n\n"
                        "The Connect button remains available for retry.")
            logging.error(f"[graphics_window.reconnect_device] Connection failed for {device_type}")
            QMessageBox.critical(self, "Connection Failed", error_msg)
            
    except Exception as e:
        # Exception during connection - show error but keep button enabled
        error_msg = (f"Error during device connection: {str(e)}\n\n"
                    "Please try the following:\n"
                    "1. Remove and reconnect the VNA device\n"
                    "2. Check USB cable and port\n"
                    "3. Restart the application if needed\n"
                    "4. Try clicking Connect again")
        logging.error(f"[graphics_window.reconnect_device] Exception during connection: {str(e)}")
        QMessageBox.critical(self, "Connection Error", error_msg)
        
    finally:
        # Reset reconnect button state
        update_reconnect_button_state(self)
        
        # Re-enable sweep button after reconnection attempt
        self.sweep_button.setEnabled(True)