"""
Touchstone Exporter for NanoVNA measurement data.

This module provides functionality to export S-parameter data to Touchstone format (.s2p files).
"""

import os
import logging
from datetime import datetime
from PySide6.QtWidgets import QMessageBox, QFileDialog


class TouchstoneExporter:
    """
    Exports NanoVNA measurement data to Touchstone format (.s2p files).
    
    Supports exporting S11 and S21 parameter data in standard Touchstone format
    for use with other RF analysis tools.
    """
    
    def __init__(self, parent_widget=None):
        """
        Initialize the Touchstone exporter.
        
        Args:
            parent_widget: Parent widget for dialog boxes (optional)
        """
        self.parent_widget = parent_widget
        self.logger = logging.getLogger(__name__)
    
    def export_to_s1p(self, freqs, s11_data, device_name=None):
        """
        Export S-parameter data to Touchstone S1P format (S11 only).
        
        Args:
            freqs: Frequency array in Hz
            s11_data: S11 parameter data (complex array)
            device_name: Optional device name for the file header
            
        Returns:
            bool: True if export successful, False otherwise
        """
        self.logger.info("Starting Touchstone S1P export")
        
        # Validate input data for S1P
        if not self._validate_s1p_data(freqs, s11_data):
            return False
        
        # Get save file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent_widget,
            "Export Touchstone S1P Data",
            "",
            "Touchstone S1P Files (*.s1p);;All Files (*)"
        )
        
        if not file_path:
            self.logger.info("S1P Export cancelled by user")
            return False
        
        # Ensure file has .s1p extension
        if not file_path.lower().endswith('.s1p'):
            file_path += '.s1p'
        
        try:
            # Export the data
            self._write_s1p_file(file_path, freqs, s11_data, device_name or "Unknown")
            
            # Success message
            self._show_success_message(file_path, freqs, format_type="S1P")
            self.logger.info(f"Successfully exported {len(freqs)} points to S1P file: {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"Error exporting Touchstone S1P data:\\n{str(e)}"
            self._show_error("Export Error", error_msg)
            self.logger.error(f"S1P Export error: {e}")
            self.logger.error(f"Exception details: {type(e).__name__}")
            return False

    def export_to_s2p(self, freqs, s11_data, s21_data, device_name=None):
        """
        Export S-parameter data to Touchstone S2P format.
        
        Args:
            freqs: Frequency array in Hz
            s11_data: S11 parameter data (complex array)
            s21_data: S21 parameter data (complex array)
            device_name: Optional device name for the file header
            
        Returns:
            bool: True if export successful, False otherwise
        """
        self.logger.info("Starting Touchstone S2P export")
        
        # Validate input data
        if not self._validate_data(freqs, s11_data, s21_data):
            return False
        
        # Get save file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent_widget,
            "Export Touchstone S2P Data",
            "",
            "Touchstone S2P Files (*.s2p);;All Files (*)"
        )
        
        if not file_path:
            self.logger.info("S2P Export cancelled by user")
            return False
        
        # Ensure file has .s2p extension
        if not file_path.lower().endswith('.s2p'):
            file_path += '.s2p'
        
        try:
            # Export the data
            self._write_s2p_file(file_path, freqs, s11_data, s21_data, device_name or "Unknown")
            
            # Success message
            self._show_success_message(file_path, freqs, format_type="S2P")
            self.logger.info(f"Successfully exported {len(freqs)} points to S2P file: {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"Error exporting Touchstone S2P data:\\n{str(e)}"
            self._show_error("Export Error", error_msg)
            self.logger.error(f"S2P Export error: {e}")
            self.logger.error(f"Exception details: {type(e).__name__}")
            return False
    
    def _validate_s1p_data(self, freqs, s11_data):
        """
        Validate input data for S1P export.
        
        Args:
            freqs: Frequency array
            s11_data: S11 data array
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        # Check if we have sweep data available
        if freqs is None:
            self._show_warning("No Data", "No sweep data available for export.\\nPlease run a sweep first.")
            self.logger.warning("No frequency data available")
            return False
        
        if s11_data is None:
            self._show_warning("No Data", "No S11 data available for export.\\nPlease run a sweep first.")
            self.logger.warning("No S11 data available")
            return False
        
        # Check data consistency
        if len(freqs) != len(s11_data):
            error_msg = f"Data length mismatch detected.\\nFreqs: {len(freqs)}, S11: {len(s11_data)}"
            self._show_error("Data Error", error_msg)
            self.logger.error(error_msg)
            return False
        
        return True

    def _validate_data(self, freqs, s11_data, s21_data):
        """
        Validate input data for export.
        
        Args:
            freqs: Frequency array
            s11_data: S11 data array
            s21_data: S21 data array
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        # Check if we have sweep data available
        if freqs is None:
            self._show_warning("No Data", "No sweep data available for export.\\nPlease run a sweep first.")
            self.logger.warning("No frequency data available")
            return False
        
        if s11_data is None:
            self._show_warning("No Data", "No S11 data available for export.\\nPlease run a sweep first.")
            self.logger.warning("No S11 data available")
            return False
            
        if s21_data is None:
            self._show_warning("No Data", "No S21 data available for export.\\nPlease run a sweep first.")
            self.logger.warning("No S21 data available")
            return False
        
        # Check data consistency
        if len(freqs) != len(s11_data) or len(freqs) != len(s21_data):
            error_msg = f"Data length mismatch detected.\\nFreqs: {len(freqs)}, S11: {len(s11_data)}, S21: {len(s21_data)}"
            self._show_error("Data Error", error_msg)
            self.logger.error(error_msg)
            return False
        
        return True
    
    def _write_s1p_file(self, file_path, freqs, s11_data, device_name):
        """
        Write data to Touchstone S1P format file.
        
        Args:
            file_path: Path where to save the S1P file
            freqs: Frequency array in Hz
            s11_data: S11 parameter data
            device_name: Name of the measurement device
        """
        self.logger.info(f"Writing S1P file: {file_path}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"! Touchstone S1P file exported from NanoVNA UTN Toolkit\n")
            f.write(f"! Device: {device_name}\n")
            f.write(f"! Export date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"! Frequency range: {freqs[0]/1e6:.3f} - {freqs[-1]/1e6:.3f} MHz\n")
            f.write(f"! Number of points: {len(freqs)}\n")
            f.write(f"! Parameter: S11 (Reflection)\n")
            f.write(f"!\n")
            f.write("# Hz S RI R 50\n")
            f.write("! f[Hz]  S11_real S11_imag\n")

            for i in range(len(freqs)):
                freq = freqs[i]
                s11 = s11_data[i]

                # Column-aligned formatting for S1P
                line = "{:<12.6e} {:<12.6f} {:<12.6f}\n".format(
                    freq,
                    s11.real, 
                    s11.imag
                )
                f.write(line)
        
        self.logger.info(f"Successfully wrote {len(freqs)} S1P data points")

    def _write_s2p_file(self, file_path, freqs, s11_data, s21_data, device_name):
        """
        Write data to Touchstone S2P format file.
        
        Args:
            file_path: Path where to save the S2P file
            freqs: Frequency array in Hz
            s11_data: S11 parameter data
            s21_data: S21 parameter data
            device_name: Name of the measurement device
        """
        self.logger.info(f"Writing S2P file: {file_path}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"! Touchstone S2P file exported from NanoVNA UTN Toolkit\n")
            f.write(f"! Device: {device_name}\n")
            f.write(f"! Export date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"! Frequency range: {freqs[0]/1e6:.3f} - {freqs[-1]/1e6:.3f} MHz\n")
            f.write(f"! Number of points: {len(freqs)}\n")
            f.write(f"! Parameters: S11, S21\n")
            f.write(f"!\n")
            f.write("# Hz S RI R 50\n")
            f.write("! f[Hz]  S11_real S11_imag S21_real S21_imag S12_real S12_imag S22_real S22_imag\n")

            for i in range(len(freqs)):
                freq = freqs[i]
                s11, s21 = s11_data[i], s21_data[i]

                s12, s22 = s21, 0+0j

                # Column-aligned formatting
                line = "{:<12.6e} {:<8.6f} {:<8.6f} {:<8.6f} {:<8.6f} {:<8.6f} {:<8.6f} {:<8.6f} {:<8.6f}\n".format(
                    freq,
                    s11.real, s11.imag,
                    s21.real, s21.imag,
                    s12.real, s12.imag,
                    s22.real, s22.imag
                )
                f.write(line)
        
        self.logger.info(f"Successfully wrote {len(freqs)} S2P data points")
    
    def _show_success_message(self, file_path, freqs, format_type="Touchstone"):
        """Show success message to user."""
        num_points = len(freqs)
        freq_range = f"{freqs[0]/1e6:.3f} - {freqs[-1]/1e6:.3f} MHz"
        success_msg = (f"{format_type} data exported successfully!\\n\\n"
                      f"File: {file_path}\\n"
                      f"Points: {num_points}\\n"
                      f"Frequency range: {freq_range}")
        self._show_info("Export Successful", success_msg)
    
    def _show_warning(self, title, message):
        """Show warning message box."""
        if self.parent_widget:
            QMessageBox.warning(self.parent_widget, title, message)
    
    def _show_info(self, title, message):
        """Show information message box."""
        if self.parent_widget:
            QMessageBox.information(self.parent_widget, title, message)
    
    def _show_error(self, title, message):
        """Show error message box."""
        if self.parent_widget:
            QMessageBox.critical(self.parent_widget, title, message)