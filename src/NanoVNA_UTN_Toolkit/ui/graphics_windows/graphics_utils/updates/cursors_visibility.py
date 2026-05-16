import sys
import os
import logging

import numpy as np

from pathlib import Path

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.sliders_update import left_slider_moved, left_slider_moved_2, right_slider_moved, right_slider_moved_2
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------------------------- #

def force_marker_visibility(self, marker_color_left, marker_color_right, marker1_size_left, marker1_size_right):
    """Force markers to be visible by recreating them directly on axes"""

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/graphics_config/graphics_config.ini",
        "ui/graphics_windows/graphics_config/graphics_config.ini", 
        Path(__file__).resolve()
    )

    unit_mode_left = settings.value("Graphic1/db_times", "dB") 
    unit_mode_right  = settings.value("Graphic2/db_times", "dB")

    logging.info(f"[graphics_window] Left panel unit mode: {unit_mode_left}")
    logging.info(f"[graphics_window] Right panel unit mode: {unit_mode_right}")

    if (hasattr(self, 'cursor_left') or hasattr(self, 'cursor_left_2')) and hasattr(self, 'ax_left') and (self.cursor_left or self.cursor_left_2) and self.ax_left:
        try:
            # Remove the old cursor first to avoid duplicates
            try:
                if self.cursor_left:
                    self.cursor_left.remove()
                    logging.info("[graphics_window._force_marker_visibility] Removed old left cursor to prevent duplicates")
            except:
                pass  # Ignore errors if cursor can't be removed
            
            # Get current data from the old cursor if possible, otherwise use defaults
            x_val, y_val = 0.0, 0.0
            try:
                x_data = self.cursor_left.get_xdata()
                y_data = self.cursor_left.get_ydata()

                if hasattr(x_data, '__len__') and hasattr(y_data, '__len__') and len(x_data) > 0 and len(y_data) > 0:
                    x_val = float(x_data[0])
                    y_val = float(y_data[0])
            except:
                pass  # Use defaults
            
            # Create new cursor directly on the axes
            new_cursor = self.ax_left.plot(x_val, y_val, 'o', color=marker_color_left, markersize=marker1_size_left, markeredgewidth=2)[0]
            self.cursor_left = new_cursor
            logging.info(f"[graphics_window._force_marker_visibility] Created new left cursor at ({x_val}, {y_val})")

            if self.cursor_left:
                self.cursor_left.set_visible(self.show_graphic1_marker1)
                self.fig_left.canvas.draw_idle()

            # Also update in markers list if it exists
            if hasattr(self, 'markers') and self.markers:
                for i, marker in enumerate(self.markers):
                    if marker and marker.get('cursor') and i == 0:  # First marker
                        marker['cursor'] = new_cursor
                            
                # Store the original update_cursor function and replace with a wrapper
                if hasattr(self, 'update_cursor') and not hasattr(self, '_original_update_cursor'):
                    self._original_update_cursor = self.update_cursor
                    
                    def cursor_left_wrapper(index, from_slider=False):
                        # Call the original function first to update labels
                        result = self._original_update_cursor(index, from_slider)
                        
                        # Then update our visible cursor position 
                        if hasattr(self, 'cursor_left') and self.cursor_left and hasattr(self.cursor_left, 'set_data'):
                            try:

                                # Load configuration for UI colors and styles
                                settings = get_settings(
                                    "INI/graphics_config/graphics_config.ini",
                                    "ui/graphics_windows/graphics_config/graphics_config.ini", 
                                    Path(__file__).resolve()
                                )

                                graph_type_left = settings.value("Tab1/GraphType1", "Smith Diagram")
                                s_param_left = settings.value("Tab1/SParameter", "S11")
                                
                                # Determine which S parameter data to use
                                s_data = None
                                if s_param_left == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                    s_data = self.s21
                                elif s_param_left == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                    s_data = self.s11
                                elif hasattr(self, 's21') and self.s21 is not None:
                                    s_data = self.s21  # Default fallback to S21
                                elif hasattr(self, 's11') and self.s11 is not None:
                                    s_data = self.s11  # Final fallback to S11
                                
                                if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                    val_complex = s_data[index]
                                    
                                    # Use appropriate coordinates based on graph type
                                    if graph_type_left == "Smith Diagram":
                                        # Smith diagram coordinates (real/imag)
                                        real_part = float(np.real(val_complex))
                                        imag_part = float(np.imag(val_complex))
                                        self.cursor_left.set_data([real_part], [imag_part])
                                    elif graph_type_left == "Magnitude":
                                        freq_mhz = float(self.freqs[index] / 1e6)
                                        if unit_mode_left == "dB":
                                            mag_val = float(20 * np.log10(np.abs(val_complex)))
                                        elif unit_mode_left == "Power ratio":
                                            mag_val = float(np.abs(val_complex)**2)
                                        elif unit_mode_left == "Voltage ratio":
                                            mag_val = float(np.abs(val_complex))
                                        else:
                                            mag_val = float(np.abs(val_complex))
                                        self.cursor_left.set_data([freq_mhz], [mag_val])
                                    elif graph_type_left == "Phase":
                                        # Phase plot coordinates (freq in MHz, phase in degrees)
                                        freq_mhz = float(self.freqs[index] / 1e6)
                                        phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                        self.cursor_left.set_data([freq_mhz], [phase_deg])
                                    elif graph_type_left == "VSWR":
                                        # VSWR plot coordinates (freq in MHz, VSWR value)
                                        freq_mhz = float(self.freqs[index] / 1e6)
                                        s_magnitude = np.abs(val_complex)
                                        vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                        self.cursor_left.set_data([freq_mhz], [float(vswr_val)])
                                    
                                    # Force redraw
                                    if hasattr(self, 'canvas_left') and self.canvas_left:
                                        self.canvas_left.draw_idle()
                            except Exception as e:
                                print(f"Error updating cursor_left position: {e}")
                        
                        return result
                    
                    self.update_cursor = cursor_left_wrapper

                    if hasattr(self, 'slider_left') and self.slider_left:
                        try:
                            self.slider_left.observers.clear()
                        except:
                            pass
                        self.slider_left.on_changed(lambda: left_slider_moved(self))
                    
                    # Reconnect the slider to use our wrapper
                    if hasattr(self, 'slider_left') and self.slider_left:
                        try:
                            self.slider_left.observers.clear()
                        except:
                            try:
                                self.slider_left.disconnect()
                            except:
                                pass
                        self.slider_left.on_changed(lambda val: cursor_left_wrapper(int(val), from_slider=True))

        except Exception as e:
            print(f"Error forcing cursor_left to ax_left: {e}")
            
    if hasattr(self, 'cursor_right') and hasattr(self, 'ax_right') and self.cursor_right and self.ax_right:
        try:
            # Remove the old cursor first to avoid duplicates
            try:
                if self.cursor_right:
                    self.cursor_right.remove()
                    logging.info("[graphics_window._force_marker_visibility] Removed old right cursor to prevent duplicates")
            except:
                pass  # Ignore errors if cursor can't be removed
            
            # Get current data from the old cursor if possible, otherwise use defaults
            x_val, y_val = 0.0, 0.0
            try:
                x_data = self.cursor_right.get_xdata()
                y_data = self.cursor_right.get_ydata()
                if hasattr(x_data, '__len__') and hasattr(y_data, '__len__') and len(x_data) > 0 and len(y_data) > 0:
                    x_val = float(x_data[0])
                    y_val = float(y_data[0])
            except:
                pass  # Use defaults
            
            # Create new cursor directly on the axes
            new_cursor = self.ax_right.plot(x_val, y_val, 'o', color=marker_color_right, markersize=marker1_size_right, markeredgewidth=2)[0]
            self.cursor_right = new_cursor
            logging.info(f"[graphics_window._force_marker_visibility] Created new right cursor at ({x_val}, {y_val})")

            if self.cursor_right:
                self.cursor_right.set_visible(self.show_graphic2_marker1)
                self.fig_right.canvas.draw_idle()
            
            if hasattr(self, 'slider_right') and self.slider_right:
                self.slider_right.on_changed(lambda val: self.update_right_cursor(int(val), from_slider=True))

            # Also update in markers list if it exists
            if hasattr(self, 'markers') and self.markers:
                for i, marker in enumerate(self.markers):
                    if marker and marker.get('cursor') and i == 1:  # Second marker
                        marker['cursor'] = new_cursor
                            
                # Store the original update_right_cursor function and replace with a wrapper
                if hasattr(self, 'update_right_cursor') and not hasattr(self, '_original_update_right_cursor'):
                    self._original_update_right_cursor = self.update_right_cursor
                    
                    def cursor_right_wrapper(index, from_slider=False):
                        # Call the original function first to update labels
                        result = self._original_update_right_cursor(index, from_slider)
                        
                        # Then update our visible cursor position 
                        if hasattr(self, 'cursor_right') and self.cursor_right and hasattr(self.cursor_right, 'set_data'):
                            try:

                                # Load configuration for UI colors and styles
                                settings = get_settings(
                                    "INI/graphics_config/graphics_config.ini",
                                    "ui/graphics_windows/graphics_config/graphics_config.ini", 
                                    Path(__file__).resolve()
                                )

                                graph_type_right = settings.value("Tab2/GraphType2", "Magnitude")
                                s_param_right = settings.value("Tab2/SParameter", "S11")
                                
                                # Determine which S parameter data to use
                                s_data = None
                                if s_param_right == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                    s_data = self.s21
                                elif s_param_right == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                    s_data = self.s11
                                elif hasattr(self, 's21') and self.s21 is not None:
                                    s_data = self.s21  # Default fallback to S21
                                elif hasattr(self, 's11') and self.s11 is not None:
                                    s_data = self.s11  # Final fallback to S11
                                
                                if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                    val_complex = s_data[index]
                                    
                                    # Use appropriate coordinates based on graph type
                                    if graph_type_right == "Smith Diagram":
                                        # Smith diagram coordinates (real/imag)
                                        real_part = float(np.real(val_complex))
                                        imag_part = float(np.imag(val_complex))
                                        self.cursor_right.set_data([real_part], [imag_part])
                                    elif graph_type_right == "Magnitude":
                                        # Magnitude plot coordinates (freq in MHz, magnitude in dB)
                                        freq_mhz = float(self.freqs[index] / 1e6)
                                        if unit_mode_right == "dB":
                                            mag_val = float(20 * np.log10(np.abs(val_complex)))
                                        elif unit_mode_right == "Power ratio":
                                            mag_val = float(np.abs(val_complex)**2)
                                        elif unit_mode_right == "Voltage ratio":
                                            mag_val = float(np.abs(val_complex))
                                        else:
                                            mag_val = float(np.abs(val_complex))
                                        self.cursor_right.set_data([freq_mhz], [mag_val])
                                    elif graph_type_right == "Phase":
                                        # Phase plot coordinates (freq in MHz, phase in degrees)
                                        freq_mhz = float(self.freqs[index] / 1e6)
                                        phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                        self.cursor_right.set_data([freq_mhz], [phase_deg])
                                    elif graph_type_right == "VSWR":
                                        # VSWR plot coordinates (freq in MHz, VSWR value)
                                        freq_mhz = float(self.freqs[index] / 1e6)
                                        s_magnitude = np.abs(val_complex)
                                        vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                        self.cursor_right.set_data([freq_mhz], [float(vswr_val)])
                                    
                                    # Force redraw
                                    if hasattr(self, 'canvas_right') and self.canvas_right:
                                        self.canvas_right.draw_idle()
                            except Exception as e:
                                print(f"Error updating cursor_right position: {e}")
                        
                        return result
                    
                    self.update_right_cursor = cursor_right_wrapper

                    if hasattr(self, 'slider_right') and self.slider_right:
                        try:
                            self.slider_right.observers.clear()
                        except:
                            pass
                        self.slider_right.on_changed(lambda: right_slider_moved(self))
                        #self.right_slider_moved()
                    
                    # Reconnect the slider to use our wrapper
                    if hasattr(self, 'slider_right') and self.slider_right:
                        try:
                            self.slider_right.observers.clear()
                        except:
                            try:
                                self.slider_right.disconnect()
                            except:
                                pass
                        self.slider_right.on_changed(lambda val: cursor_right_wrapper(int(val), from_slider=True))
            
        except Exception as e:
            print(f"Error forcing cursor_right to ax_right: {e}")

def force_marker_visibility_2(self, marker_color_left, marker_color_right, marker_size_left, marker_size_right):
        """Force markers to be visible by recreating them directly on axes"""

        # Load configuration for UI colors and styles

        settings = get_settings(
            "INI/graphics_config/graphics_config.ini",
            "ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        unit_mode_left = settings.value("Graphic1/db_times", "dB") 
        unit_mode_right  = settings.value("Graphic2/db_times", "dB")

        logging.info(f"[graphics_window] Left panel unit mode: {unit_mode_left}")
        logging.info(f"[graphics_window] Right panel unit mode: {unit_mode_right}")
        
        if hasattr(self, 'cursor_left_2') and hasattr(self, 'ax_left') and self.cursor_left_2 and self.ax_left:
            try:
                # Remove the old cursor first to avoid duplicates
                try:
                    if self.cursor_left_2:
                        self.cursor_left_2.remove()
                        logging.info("[graphics_window._force_marker_visibility] Removed old left cursor to prevent duplicates")
                except:
                    pass  # Ignore errors if cursor can't be removed
                
                # Get current data from the old cursor if possible, otherwise use defaults
                x_val, y_val = 0.0, 0.0
                try:
                    x_data_2 = self.cursor_left_2.get_xdata()
                    y_data_2 = self.cursor_left_2.get_ydata()

                    if hasattr(x_data_2, '__len__') and hasattr(y_data_2, '__len__') and len(x_data_2) > 0 and len(y_data_2) > 0:
                        x_val_2 = float(y_data_2[0])
                        y_val_2 = float(y_data_2[0])
                except:
                    pass  # Use defaults
                
                # Create new cursor directly on the axes
                new_cursor_2 = self.ax_left.plot(x_val_2, y_val_2, 'o', color=marker_color_left, markersize=marker_size_left, markeredgewidth=2, visible=self.show_graphic1_marker2)[0]
                self.cursor_left_2 = new_cursor_2
                logging.info(f"[graphics_window._force_marker_visibility] Created new left cursor at ({x_val_2}, {y_val_2})")

                if hasattr(self, 'slider_left_2') and self.slider_left_2:
                    self.slider_left_2.on_changed(lambda val: self.update_cursor_2(int(val), from_slider=True))
                
                # Also update in markers list if it exists
                if hasattr(self, 'markers') and self.markers:
                    for i, marker in enumerate(self.markers):
                        if marker and marker.get('cursor_2') and i == 0:  # First marker
                            marker['cursor_2'] = new_cursor_2
                                
                    # Store the original update_cursor function and replace with a wrapper
                    if hasattr(self, 'update_cursor_2') and not hasattr(self, '_original_update_cursor_2'):
                        self._original_update_cursor_2 = self.update_cursor_2
                        
                        def cursor_left_wrapper_2(index, from_slider=False):
                            # Call the original function first to update labels
                            result = self._original_update_cursor_2(index, from_slider)
                            
                            # Then update our visible cursor position 
                    
                            if hasattr(self, 'cursor_left') and self.cursor_left and hasattr(self.cursor_left, 'set_data'):
                                try:

                                    # Load configuration for UI colors and styles
                                    settings = get_settings(
                                        "INI/graphics_config/graphics_config.ini",
                                        "ui/graphics_windows/graphics_config/graphics_config.ini", 
                                        Path(__file__).resolve()
                                    )

                                    graph_type_left = settings.value("Tab1/GraphType1", "Smith Diagram")
                                    s_param_left = settings.value("Tab1/SParameter", "S11")
                                    
                                    # Determine which S parameter data to use
                                    s_data = None
                                    if s_param_left == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21
                                    elif s_param_left == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11
                                    elif hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21  # Default fallback to S21
                                    elif hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11  # Final fallback to S11
                                    
                                    if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                        val_complex = s_data[index]
                                        
                                        # Use appropriate coordinates based on graph type
                                        if graph_type_left == "Smith Diagram":
                                            # Smith diagram coordinates (real/imag)
                                            real_part = float(np.real(val_complex))
                                            imag_part = float(np.imag(val_complex))
                                            self.cursor_left_2.set_data([real_part], [imag_part])
                                        elif graph_type_left == "Magnitude":
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            if unit_mode_left == "dB":
                                                mag_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_left == "Power ratio":
                                                mag_val = float(np.abs(val_complex)**2)
                                            elif unit_mode_left == "Voltage ratio":
                                                mag_val = float(np.abs(val_complex))
                                            else:
                                                mag_val = float(np.abs(val_complex))
                                            self.cursor_left_2.set_data([freq_mhz], [mag_val])
                                        elif graph_type_left == "Phase":
                                            # Phase plot coordinates (freq in MHz, phase in degrees)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                            self.cursor_left_2.set_data([freq_mhz], [phase_deg])
                                        elif graph_type_left == "VSWR":
                                            # VSWR plot coordinates (freq in MHz, VSWR value)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            s_magnitude = np.abs(val_complex)
                                            vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                            self.cursor_left_2.set_data([freq_mhz], [float(vswr_val)])
                                        
                                        # Force redraw
                                        if hasattr(self, 'canvas_left') and self.canvas_left:
                                            self.canvas_left.draw_idle()
                                except Exception as e:
                                    print(f"Error updating cursor_left position: {e}")
                        
                            return result
                
                        self.update_cursor_2 = cursor_left_wrapper_2

                        if hasattr(self, 'slider_left_2') and self.slider_left_2:
                            try:
                                self.slider_left_2.observers.clear()
                            except:
                                pass
                            self.slider_left_2.on_changed(lambda: left_slider_moved_2(self))
                        
                        # Reconnect the slider to use our wrapper
                        if hasattr(self, 'slider_left_2') and self.slider_left_2:
                            try:
                                self.slider_left_2.observers.clear()
                            except:
                                try:
                                    self.slider_left_2.disconnect()
                                except:
                                    pass
                            self.slider_left_2.on_changed(lambda val: cursor_left_wrapper_2(int(val), from_slider=True))

            except Exception as e:
                print(f"Error forcing cursor_left to ax_left: {e}")

        if hasattr(self, 'cursor_right_2') and hasattr(self, 'ax_right') and self.cursor_right_2 and self.ax_right:
            try:
                # Remove the old cursor first to avoid duplicates
                try:
                    if self.cursor_right_2:
                        self.cursor_right_2.remove()
                        logging.info("[graphics_window._force_marker_visibility] Removed old right cursor to prevent duplicates")
                except:
                    pass  # Ignore errors if cursor can't be removed
                
                # Get current data from the old cursor if possible, otherwise use defaults
                x_val, y_val = 0.0, 0.0
                try:
                    x_data = self.cursor_right_2.get_xdata()
                    y_data = self.cursor_right_2.get_ydata()
                    if hasattr(x_data, '__len__') and hasattr(y_data, '__len__') and len(x_data) > 0 and len(y_data) > 0:
                        x_val = float(x_data[0])
                        y_val = float(y_data[0])
                except:
                    pass  # Use defaults
                
                # Create new cursor directly on the axes
                new_cursor = self.ax_right.plot(x_val, y_val, 'o', color=marker_color_right, markersize=marker_size_right, markeredgewidth=2, visible=self.show_graphic2_marker2)[0]
                self.cursor_right_2 = new_cursor
                logging.info(f"[graphics_window._force_marker_visibility] Created new right cursor at ({x_val}, {y_val})")
                
                if hasattr(self, 'slider_right_2') and self.slider_right_2:
                    self.slider_right_2.on_changed(lambda val: self.update_right_cursor_2(int(val), from_slider=True))

                # Also update in markers list if it exists
                if hasattr(self, 'markers') and self.markers:
                    for i, marker in enumerate(self.markers):
                        if marker and marker.get('cursor_2') and i == 1:  # Second marker
                            marker['cursor_2'] = new_cursor
                                
                    # Store the original update_right_cursor function and replace with a wrapper
                    if hasattr(self, 'update_right_cursor_2') and not hasattr(self, '_original_update_right_cursor_2'):
                        self._original_update_right_cursor_2 = self.update_right_cursor_2
                        
                        def cursor_right_wrapper_2(index, from_slider=False):
                            # Call the original function first to update labels
                            result = self._original_update_right_cursor_2(index, from_slider)
                            
                            # Then update our visible cursor position 
                            if hasattr(self, 'cursor_right_2') and self.cursor_right_2 and hasattr(self.cursor_right_2, 'set_data'):
                                try:
 
                                    # Load configuration for UI colors and styles
                                    settings = get_settings(
                                        "INI/graphics_config/graphics_config.ini",
                                        "ui/graphics_windows/graphics_config/graphics_config.ini", 
                                        Path(__file__).resolve()
                                    )

                                    graph_type_right = settings.value("Tab2/GraphType2", "Magnitude")
                                    s_param_right = settings.value("Tab2/SParameter", "S11")
                                    
                                    # Determine which S parameter data to use
                                    s_data = None
                                    if s_param_right == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21
                                    elif s_param_right == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11
                                    elif hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21  # Default fallback to S21
                                    elif hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11  # Final fallback to S11
                                    
                                    if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                        val_complex = s_data[index]
                                        
                                        # Use appropriate coordinates based on graph type
                                        if graph_type_right == "Smith Diagram":
                                            # Smith diagram coordinates (real/imag)
                                            real_part = float(np.real(val_complex))
                                            imag_part = float(np.imag(val_complex))
                                            self.cursor_right_2.set_data([real_part], [imag_part])
                                        elif graph_type_right == "Magnitude":
                                            # Magnitude plot coordinates (freq in MHz, magnitude in dB)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            if unit_mode_right == "dB":
                                                mag_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_right == "Power ratio":
                                                mag_val = float(np.abs(val_complex)**2)
                                            elif unit_mode_right == "Voltage ratio":
                                                mag_val = float(np.abs(val_complex))
                                            else:
                                                mag_val = float(np.abs(val_complex))
                                            self.cursor_right_2.set_data([freq_mhz], [mag_val])
                                        elif graph_type_right == "Phase":
                                            # Phase plot coordinates (freq in MHz, phase in degrees)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                            self.cursor_right_2.set_data([freq_mhz], [phase_deg])
                                        elif graph_type_right == "VSWR":
                                            # VSWR plot coordinates (freq in MHz, VSWR value)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            s_magnitude = np.abs(val_complex)
                                            vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                            self.cursor_right_2.set_data([freq_mhz], [float(vswr_val)])
                                        
                                        # Force redraw
                                        if hasattr(self, 'canvas_right') and self.canvas_right:
                                            self.canvas_right.draw_idle()
                                except Exception as e:
                                    print(f"Error updating cursor_right position: {e}")
                            
                            return result
                        
                        self.update_right_cursor_2 = cursor_right_wrapper_2

                        if hasattr(self, 'slider_right_2') and self.slider_right_2:
                            try:
                                self.slider_right_2.observers.clear()
                            except:
                                pass
                            self.slider_right_2.on_changed(lambda: right_slider_moved_2(self))
                            self.right_slider_moved_2(int(0))   # antes val
                        
                        # Reconnect the slider to use our wrapper
                        if hasattr(self, 'slider_right_2') and self.slider_right_2:
                            try:
                                self.slider_right_2.observers.clear()
                            except:
                                try:
                                    self.slider_right_2.disconnect()
                                except:
                                    pass
                            self.slider_right_2.on_changed(lambda val: cursor_right_wrapper_2(int(val), from_slider=True))
                
            except Exception as e:
                print(f"Error forcing cursor_right to ax_right: {e}")

def toggle_marker_visibility(self, marker_index, show=True):
    marker = self.markers[marker_index]
    cursor = marker["cursor"]
    slider = marker["slider"]
    labels = marker["label"]
    update_cursor_func = marker.get("update_cursor", None)

    logging.info(f"cursor data: {cursor.get_data()}")

    # Check if cursor is valid before using it
    if cursor is None or cursor.figure is None:
        logging.warning(f"[graphics_window.toggle_marker_visibility] Cursor {marker_index} is invalid, skipping toggle")
        return

    cursor.set_visible(show)

    if marker_index == 0:  
        slider = self.slider_left
        slider_2 = self.slider_left_2
        fig = self.fig_left
    elif marker_index == 1: 
        slider = self.slider_right
        slider_2 = self.slider_right_2
        fig = self.fig_right
    else:
        logging.warning(f"[move_marker2_slider_left] Invalid marker_index {marker_index}")
        return

    if show:
        slider_2.ax.set_position([0.55,0.04,0.35,0.03])

        slider.ax.set_visible(True)
        slider.set_active(True)
        if hasattr(marker, "slider_callback"):
            slider.on_changed(marker.slider_callback)

        if update_cursor_func:
            update_cursor_func(0)

        edit_value = labels["freq"]
        edit_value.setEnabled(True)
        if self.freqs is not None and len(self.freqs) > 0:
            if self.freqs[0] < 1e6:  
                edit_value.setText(f"{self.freqs[0]/1e3:.3f}")
            elif self.freqs[0] < 1e9:  
                edit_value.setText(f"{self.freqs[0]/1e6:.3f}")
            else: 
                edit_value.setText(f"{self.freqs[0]/1e9:.3f}")
        else:
            edit_value.setText("--") 

    else:
        slider.set_val(0)
        slider.ax.set_visible(False)
        slider.set_active(False)

        edit_value = labels["freq"]
        edit_value.setEnabled(False)
        edit_value.setText("0")

        # --- Limpiar otros labels ---
        labels["val"].setText(f"{self.left_s_param if marker_index==0 else 'S11'}: -- + j--")
        labels["mag"].setText("|S11|: --")
        labels["phase"].setText("Phase: --")
        labels["z"].setText("Z: -- + j--")
        labels["il"].setText("IL: --")
        labels["vswr"].setText("VSWR: --")

        slider_2.ax.set_position([0.25,0.04,0.5,0.03])

    # Only draw if cursor and figure are valid
    if cursor is not None and cursor.figure is not None and cursor.figure.canvas is not None:
        cursor.figure.canvas.draw_idle()
    else:
        logging.warning(f"[graphics_window.toggle_marker_visibility] Cannot draw cursor {marker_index}, figure or canvas is None")

def toggle_marker2_visibility(self, marker_index, show_markers):
    """
    Move Marker 2 slider to the left of the corresponding canvas
    without hiding or deactivating it.
    """
    marker_2 = self.markers[marker_index]

    cursor_2 = marker_2["cursor_2"]
    slider_2 = marker_2["slider_2"]
    labels_2 = marker_2["label_2"]

    update_cursor_func_2 = marker_2.get("update_cursor_2", None)

    logging.info(f"cursor_2 data: {cursor_2.get_data()}")

    if cursor_2 is None or cursor_2.figure is None:
        logging.warning(f"[graphics_window.toggle_marker_visibility_2] Cursor {marker_index} is invalid, skipping toggle")
        return

    cursor_2.set_visible(show_markers)

    if marker_index == 0:  
        slider = self.slider_left
        slider_2 = self.slider_left_2
        fig = self.fig_left
    elif marker_index == 1: 
        slider = self.slider_right
        slider_2 = self.slider_right_2
        fig = self.fig_right
    else:
        logging.warning(f"[move_marker2_slider_left] Invalid marker_index {marker_index}")
        return

    if show_markers:

        slider_2.ax.set_visible(True)
        slider_2.set_active(True)

        slider.ax.set_position([0.1, 0.04, 0.35, 0.03])

        #slider_2.on_changed(lambda val: update_cursor(int(val), from_slider=True))

        if slider.ax.figure is not None:
            slider.ax.figure.canvas.draw_idle()

        if update_cursor_func_2:
            update_cursor_func_2(0)

        edit_value_2 = labels_2["freq"]
        edit_value_2.setEnabled(True)
        if self.freqs is not None and len(self.freqs) > 0:
            if self.freqs[0] < 1e6:  
                edit_value_2.setText(f"{self.freqs[0]/1e3:.3f}")
            elif self.freqs[0] < 1e9:  
                edit_value_2.setText(f"{self.freqs[0]/1e6:.3f}")
            else: 
                edit_value_2.setText(f"{self.freqs[0]/1e9:.3f}")
        else:
            edit_value_2.setText("--") 

    elif not show_markers:

        slider_2.set_val(0)
        slider_2.ax.set_visible(False)
        slider_2.set_active(False) 

        # --- Limpiar otros labels ---
        labels_2["val"].setText(f"{self.left_s_param if marker_index==0 else 'S11'}: -- + j--")
        labels_2["mag"].setText("|S11|: --")
        labels_2["phase"].setText("Phase: --")
        labels_2["z"].setText("Z: -- + j--")
        labels_2["il"].setText("IL: --")
        labels_2["vswr"].setText("VSWR: --")

        slider.ax.set_position([0.25,0.04,0.5,0.03])

    # Only draw if cursor and figure are valid
    if cursor_2 is not None and cursor_2.figure is not None and cursor_2.figure.canvas is not None:
        cursor_2.figure.canvas.draw_idle()
    else:
        logging.warning(f"[graphics_window.toggle_marker_visibility] Cannot draw cursor {marker_index}, figure or canvas is None")
