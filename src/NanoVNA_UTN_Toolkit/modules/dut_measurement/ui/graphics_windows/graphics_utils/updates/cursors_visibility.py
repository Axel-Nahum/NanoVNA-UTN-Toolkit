from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

import numpy as np

from pathlib import Path

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

left_slider_moved, left_slider_moved_2, right_slider_moved, right_slider_moved_2 = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.sliders_update", "left_slider_moved", "left_slider_moved_2", "right_slider_moved", "right_slider_moved_2")

# ----------------------------------------------------------------------------------------------------------------------------------- #

def force_marker_visibility(self, marker_color_left, marker_color_right, marker1_size_left, marker1_size_right):
    """Force markers to be visible by recreating them directly on axes"""

    logging.info(f"[force_marker_visibility] self.markers = {getattr(self, 'markers', 'NO EXISTE')}")
    logging.info(f"[force_marker_visibility] show_graphic1_marker1 = {getattr(self, 'show_graphic1_marker1', 'NO EXISTE')}")
    logging.info(f"[force_marker_visibility] show_graphic2_marker1 = {getattr(self, 'show_graphic2_marker1', 'NO EXISTE')}")

    settings = get_settings(
        "INI/dut_measurement/graphics_config/graphics_config.ini",
        "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
        Path(__file__).resolve()
    )
    unit_mode_left = settings.value("Graphic1/db_times", "dB")
    unit_mode_right = settings.value("Graphic2/db_times", "dB")

    logging.info(f"[graphics_window] Left panel unit mode: {unit_mode_left}")
    logging.info(f"[graphics_window] Right panel unit mode: {unit_mode_right}")

    # ------------------------------------------------------------------ #
    # cursor_left
    # ------------------------------------------------------------------ #
    if hasattr(self, 'cursor_left') and hasattr(self, 'ax_left') and self.cursor_left and self.ax_left:
        try:
            try:
                if self.cursor_left:
                    self.cursor_left.remove()
                    logging.info("[force_marker_visibility] Removed old left cursor")
            except:
                pass

            new_cursor = self.ax_left.plot(0.0, 0.0, 'o', color=marker_color_left, markersize=marker1_size_left, markeredgewidth=2, visible=self.show_graphic1_marker1)[0]
            self.cursor_left = new_cursor
            logging.info("[force_marker_visibility] Created new left cursor at (0, 0)")

            # Update markers list if it exists
            if hasattr(self, 'markers') and self.markers:
                for i, marker in enumerate(self.markers):
                    if marker and marker.get('cursor') and i == 0:
                        marker['cursor'] = new_cursor

            # FIX: wrapper and slider reconnection OUTSIDE of if markers block
            if hasattr(self, 'update_cursor'):
                if hasattr(self, '_original_update_cursor'):
                    self.update_cursor = self._original_update_cursor
                self._original_update_cursor = self.update_cursor

                def cursor_left_wrapper(index, from_slider=False):
                    result = self._original_update_cursor(index, from_slider)

                    if hasattr(self, 'cursor_left') and self.cursor_left and hasattr(self.cursor_left, 'set_data'):
                        try:
                            settings = get_settings(
                                "INI/dut_measurement/graphics_config/graphics_config.ini",
                                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                                Path(__file__).resolve()
                            )

                            graph_type_left = settings.value("Tab1/GraphType1", "Smith Diagram")
                            s_param_left = settings.value("Tab1/SParameter", "S11")

                            s_data = None
                            if s_param_left == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif s_param_left == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11
                            elif hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11

                            if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                val_complex = s_data[index]

                                if graph_type_left == "Smith Diagram":
                                    self.cursor_left.set_data([float(np.real(val_complex))], [float(np.imag(val_complex))])
                                else:
                                    freq_mhz = float(self.freqs[index] / 1e6)
                                    y_val = None
                                    # Read Y directly from the plotted line so the cursor always
                                    # matches the trace (avoids phase-wrapping and unit mismatches)
                                    if hasattr(self, 'line_left') and self.line_left is not None:
                                        try:
                                            ydata = self.line_left.get_ydata()
                                            if ydata is not None and len(ydata) > index:
                                                y_val = float(ydata[index])
                                        except Exception:
                                            pass
                                    if y_val is None:
                                        if graph_type_left == "Magnitude":
                                            if unit_mode_left == "dB":
                                                y_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_left == "Power ratio":
                                                y_val = float(np.abs(val_complex) ** 2)
                                            else:
                                                y_val = float(np.abs(val_complex))
                                        elif graph_type_left == "Phase":
                                            y_val = float(np.angle(val_complex) * 180 / np.pi)
                                        elif graph_type_left == "VSWR":
                                            s_mag = np.abs(val_complex)
                                            y_val = float((1 + s_mag) / (1 - s_mag)) if s_mag < 1 else 999.0
                                        else:
                                            y_val = float(np.abs(val_complex))
                                    self.cursor_left.set_data([freq_mhz], [y_val])

                                if hasattr(self, 'canvas_left') and self.canvas_left:
                                    self.canvas_left.draw_idle()
                        except Exception as e:
                            logging.warning(f"Error updating cursor_left position: {e}")

                    return result

                self.update_cursor = cursor_left_wrapper

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
            logging.warning(f"Error forcing cursor_left to ax_left: {e}")

    # ------------------------------------------------------------------ #
    # cursor_right
    # ------------------------------------------------------------------ #
    if hasattr(self, 'cursor_right') and hasattr(self, 'ax_right') and self.cursor_right and self.ax_right:
        try:
            try:
                if self.cursor_right:
                    self.cursor_right.remove()
                    logging.info("[force_marker_visibility] Removed old right cursor")
            except:
                pass

            new_cursor = self.ax_right.plot(0.0, 0.0, 'o', color=marker_color_right, markersize=marker1_size_right, markeredgewidth=2, visible=self.show_graphic2_marker1)[0]
            self.cursor_right = new_cursor
            logging.info("[force_marker_visibility] Created new right cursor at (0, 0)")

            if hasattr(self, 'fig_right') and self.fig_right:
                self.fig_right.canvas.draw_idle()

            # Update markers list if it exists
            if hasattr(self, 'markers') and self.markers:
                for i, marker in enumerate(self.markers):
                    if marker and marker.get('cursor') and i == 1:
                        marker['cursor'] = new_cursor

            # FIX: wrapper and slider reconnection OUTSIDE of if markers block
            if hasattr(self, 'update_right_cursor'):
                if hasattr(self, '_original_update_right_cursor'):
                    self.update_right_cursor = self._original_update_right_cursor
                self._original_update_right_cursor = self.update_right_cursor

                def cursor_right_wrapper(index, from_slider=False):
                    result = self._original_update_right_cursor(index, from_slider)

                    if hasattr(self, 'cursor_right') and self.cursor_right and hasattr(self.cursor_right, 'set_data'):
                        try:
                            settings = get_settings(
                                "INI/dut_measurement/graphics_config/graphics_config.ini",
                                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                                Path(__file__).resolve()
                            )

                            graph_type_right = settings.value("Tab2/GraphType2", "Magnitude")
                            s_param_right = settings.value("Tab2/SParameter", "S11")

                            s_data = None
                            if s_param_right == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif s_param_right == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11
                            elif hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11

                            if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                val_complex = s_data[index]

                                if graph_type_right == "Smith Diagram":
                                    self.cursor_right.set_data([float(np.real(val_complex))], [float(np.imag(val_complex))])
                                else:
                                    freq_mhz = float(self.freqs[index] / 1e6)
                                    y_val = None
                                    if hasattr(self, 'line_right') and self.line_right is not None:
                                        try:
                                            ydata = self.line_right.get_ydata()
                                            if ydata is not None and len(ydata) > index:
                                                y_val = float(ydata[index])
                                        except Exception:
                                            pass
                                    if y_val is None:
                                        if graph_type_right == "Magnitude":
                                            if unit_mode_right == "dB":
                                                y_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_right == "Power ratio":
                                                y_val = float(np.abs(val_complex) ** 2)
                                            else:
                                                y_val = float(np.abs(val_complex))
                                        elif graph_type_right == "Phase":
                                            y_val = float(np.angle(val_complex) * 180 / np.pi)
                                        elif graph_type_right == "VSWR":
                                            s_mag = np.abs(val_complex)
                                            y_val = float((1 + s_mag) / (1 - s_mag)) if s_mag < 1 else 999.0
                                        else:
                                            y_val = float(np.abs(val_complex))
                                    self.cursor_right.set_data([freq_mhz], [y_val])

                                if hasattr(self, 'canvas_right') and self.canvas_right:
                                    self.canvas_right.draw_idle()
                        except Exception as e:
                            logging.warning(f"Error updating cursor_right position: {e}")

                    return result

                self.update_right_cursor = cursor_right_wrapper

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
            logging.warning(f"Error forcing cursor_right to ax_right: {e}")


def force_marker_visibility_2(self, marker_color_left, marker_color_right, marker_size_left, marker_size_right):
    """Force markers 2 to be visible by recreating them directly on axes"""

    settings = get_settings(
        "INI/dut_measurement/graphics_config/graphics_config.ini",
        "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
        Path(__file__).resolve()
    )
    unit_mode_left = settings.value("Graphic1/db_times", "dB")
    unit_mode_right = settings.value("Graphic2/db_times", "dB")

    logging.info(f"[graphics_window] Left panel unit mode: {unit_mode_left}")
    logging.info(f"[graphics_window] Right panel unit mode: {unit_mode_right}")

    # ------------------------------------------------------------------ #
    # cursor_left_2
    # ------------------------------------------------------------------ #
    if hasattr(self, 'cursor_left_2') and hasattr(self, 'ax_left') and self.cursor_left_2 and self.ax_left:
        try:
            try:
                if self.cursor_left_2:
                    self.cursor_left_2.remove()
                    logging.info("[force_marker_visibility_2] Removed old left cursor_2")
            except:
                pass

            new_cursor_2 = self.ax_left.plot(0.0, 0.0, 'o', color=marker_color_left, markersize=marker_size_left, markeredgewidth=2, visible=self.show_graphic1_marker2)[0]
            self.cursor_left_2 = new_cursor_2
            logging.info("[force_marker_visibility_2] Created new left cursor_2 at (0, 0)")

            # Update markers list if it exists
            if hasattr(self, 'markers') and self.markers:
                for i, marker in enumerate(self.markers):
                    if marker and marker.get('cursor_2') and i == 0:
                        marker['cursor_2'] = new_cursor_2

            # FIX: wrapper and slider reconnection OUTSIDE of if markers block
            if hasattr(self, 'update_cursor_2'):
                if hasattr(self, '_original_update_cursor_2'):
                    self.update_cursor_2 = self._original_update_cursor_2
                self._original_update_cursor_2 = self.update_cursor_2

                def cursor_left_wrapper_2(index, from_slider=False):
                    result = self._original_update_cursor_2(index, from_slider)

                    if hasattr(self, 'cursor_left_2') and self.cursor_left_2 and hasattr(self.cursor_left_2, 'set_data'):
                        try:
                            settings = get_settings(
                                "INI/dut_measurement/graphics_config/graphics_config.ini",
                                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                                Path(__file__).resolve()
                            )

                            graph_type_left = settings.value("Tab1/GraphType1", "Smith Diagram")
                            s_param_left = settings.value("Tab1/SParameter", "S11")

                            s_data = None
                            if s_param_left == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif s_param_left == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11
                            elif hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11

                            if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                val_complex = s_data[index]

                                if graph_type_left == "Smith Diagram":
                                    self.cursor_left_2.set_data([float(np.real(val_complex))], [float(np.imag(val_complex))])
                                else:
                                    freq_mhz = float(self.freqs[index] / 1e6)
                                    y_val = None
                                    if hasattr(self, 'line_left') and self.line_left is not None:
                                        try:
                                            ydata = self.line_left.get_ydata()
                                            if ydata is not None and len(ydata) > index:
                                                y_val = float(ydata[index])
                                        except Exception:
                                            pass
                                    if y_val is None:
                                        if graph_type_left == "Magnitude":
                                            if unit_mode_left == "dB":
                                                y_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_left == "Power ratio":
                                                y_val = float(np.abs(val_complex) ** 2)
                                            else:
                                                y_val = float(np.abs(val_complex))
                                        elif graph_type_left == "Phase":
                                            y_val = float(np.angle(val_complex) * 180 / np.pi)
                                        elif graph_type_left == "VSWR":
                                            s_mag = np.abs(val_complex)
                                            y_val = float((1 + s_mag) / (1 - s_mag)) if s_mag < 1 else 999.0
                                        else:
                                            y_val = float(np.abs(val_complex))
                                    self.cursor_left_2.set_data([freq_mhz], [y_val])

                                if hasattr(self, 'canvas_left') and self.canvas_left:
                                    self.canvas_left.draw_idle()
                        except Exception as e:
                            logging.warning(f"Error updating cursor_left_2 position: {e}")

                    return result

                self.update_cursor_2 = cursor_left_wrapper_2

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
            logging.warning(f"Error forcing cursor_left_2 to ax_left: {e}")

    # ------------------------------------------------------------------ #
    # cursor_right_2
    # ------------------------------------------------------------------ #
    if hasattr(self, 'cursor_right_2') and hasattr(self, 'ax_right') and self.cursor_right_2 and self.ax_right:
        try:
            try:
                if self.cursor_right_2:
                    self.cursor_right_2.remove()
                    logging.info("[force_marker_visibility_2] Removed old right cursor_2")
            except:
                pass

            new_cursor = self.ax_right.plot(0.0, 0.0, 'o', color=marker_color_right, markersize=marker_size_right, markeredgewidth=2, visible=self.show_graphic2_marker2)[0]
            self.cursor_right_2 = new_cursor
            logging.info("[force_marker_visibility_2] Created new right cursor_2 at (0, 0)")

            # Update markers list if it exists
            if hasattr(self, 'markers') and self.markers:
                for i, marker in enumerate(self.markers):
                    if marker and marker.get('cursor_2') and i == 1:
                        marker['cursor_2'] = new_cursor

            # FIX: wrapper and slider reconnection OUTSIDE of if markers block
            if hasattr(self, 'update_right_cursor_2'):
                if hasattr(self, '_original_update_right_cursor_2'):
                    self.update_right_cursor_2 = self._original_update_right_cursor_2
                self._original_update_right_cursor_2 = self.update_right_cursor_2

                def cursor_right_wrapper_2(index, from_slider=False):
                    result = self._original_update_right_cursor_2(index, from_slider)

                    if hasattr(self, 'cursor_right_2') and self.cursor_right_2 and hasattr(self.cursor_right_2, 'set_data'):
                        try:
                            settings = get_settings(
                                "INI/dut_measurement/graphics_config/graphics_config.ini",
                                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                                Path(__file__).resolve()
                            )

                            graph_type_right = settings.value("Tab2/GraphType2", "Magnitude")
                            s_param_right = settings.value("Tab2/SParameter", "S11")

                            s_data = None
                            if s_param_right == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif s_param_right == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11
                            elif hasattr(self, 's21') and self.s21 is not None:
                                s_data = self.s21
                            elif hasattr(self, 's11') and self.s11 is not None:
                                s_data = self.s11

                            if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                val_complex = s_data[index]

                                if graph_type_right == "Smith Diagram":
                                    self.cursor_right_2.set_data([float(np.real(val_complex))], [float(np.imag(val_complex))])
                                else:
                                    freq_mhz = float(self.freqs[index] / 1e6)
                                    y_val = None
                                    if hasattr(self, 'line_right') and self.line_right is not None:
                                        try:
                                            ydata = self.line_right.get_ydata()
                                            if ydata is not None and len(ydata) > index:
                                                y_val = float(ydata[index])
                                        except Exception:
                                            pass
                                    if y_val is None:
                                        if graph_type_right == "Magnitude":
                                            if unit_mode_right == "dB":
                                                y_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_right == "Power ratio":
                                                y_val = float(np.abs(val_complex) ** 2)
                                            else:
                                                y_val = float(np.abs(val_complex))
                                        elif graph_type_right == "Phase":
                                            y_val = float(np.angle(val_complex) * 180 / np.pi)
                                        elif graph_type_right == "VSWR":
                                            s_mag = np.abs(val_complex)
                                            y_val = float((1 + s_mag) / (1 - s_mag)) if s_mag < 1 else 999.0
                                        else:
                                            y_val = float(np.abs(val_complex))
                                    self.cursor_right_2.set_data([freq_mhz], [y_val])

                                if hasattr(self, 'canvas_right') and self.canvas_right:
                                    self.canvas_right.draw_idle()
                        except Exception as e:
                            logging.warning(f"Error updating cursor_right_2 position: {e}")

                    return result

                self.update_right_cursor_2 = cursor_right_wrapper_2

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
            logging.warning(f"Error forcing cursor_right_2 to ax_right: {e}")


def toggle_marker_visibility(self, marker_index, show=True):
    marker = self.markers[marker_index]
    cursor = marker["cursor"]
    slider = marker["slider"]
    labels = marker["label"]
    update_cursor_func = marker.get("update_cursor", None)

    logging.info(f"cursor data: {cursor.get_data()}")

    if cursor is None or cursor.figure is None:
        logging.warning(f"[toggle_marker_visibility] Cursor {marker_index} is invalid, skipping toggle")
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
        logging.warning(f"[toggle_marker_visibility] Invalid marker_index {marker_index}")
        return

    if show:
        slider_2.ax.set_position([0.55, 0.04, 0.35, 0.03])

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

        labels["val"].setText(f"{self.left_s_param if marker_index==0 else 'S11'}: -- + j--")
        labels["mag"].setText("|S11|: --")
        labels["phase"].setText(f"{self.measurement_ui_s_parameter_phase} --")
        labels["z"].setText("Z: -- + j--")
        labels["il"].setText(f"{self.measurement_ui_dut_insertion_loss} --")
        labels["vswr"].setText(f"{self.measurement_ui_dut_vswr} --")

        slider_2.ax.set_position([0.25, 0.04, 0.5, 0.03])

    if cursor is not None and cursor.figure is not None and cursor.figure.canvas is not None:
        cursor.figure.canvas.draw_idle()
    else:
        logging.warning(f"[toggle_marker_visibility] Cannot draw cursor {marker_index}")


def toggle_marker2_visibility(self, marker_index, show_markers):
    marker_2 = self.markers[marker_index]

    cursor_2 = marker_2["cursor_2"]
    slider_2 = marker_2["slider_2"]
    labels_2 = marker_2["label_2"]

    update_cursor_func_2 = marker_2.get("update_cursor_2", None)

    logging.info(f"cursor_2 data: {cursor_2.get_data()}")

    if cursor_2 is None or cursor_2.figure is None:
        logging.warning(f"[toggle_marker2_visibility] Cursor {marker_index} is invalid, skipping toggle")
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
        logging.warning(f"[toggle_marker2_visibility] Invalid marker_index {marker_index}")
        return

    if show_markers:
        slider_2.ax.set_visible(True)
        slider_2.set_active(True)

        slider.ax.set_position([0.1, 0.04, 0.35, 0.03])

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

    else:
        slider_2.set_val(0)
        slider_2.ax.set_visible(False)
        slider_2.set_active(False)

        labels_2["val"].setText(f"{self.left_s_param if marker_index==0 else 'S11'}: -- + j--")
        labels_2["mag"].setText("|S11|: --")
        labels_2["phase"].setText(f"{self.measurement_ui_s_parameter_phase} --")
        labels_2["z"].setText("Z: -- + j--")
        labels_2["il"].setText(f"{self.measurement_ui_dut_insertion_loss} --")
        labels_2["vswr"].setText(f"{self.measurement_ui_dut_vswr} --")

        slider.ax.set_position([0.25, 0.04, 0.5, 0.03])

    if cursor_2 is not None and cursor_2.figure is not None and cursor_2.figure.canvas is not None:
        cursor_2.figure.canvas.draw_idle()
    else:
        logging.warning(f"[toggle_marker2_visibility] Cannot draw cursor_2 {marker_index}")