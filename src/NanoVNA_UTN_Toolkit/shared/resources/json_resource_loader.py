try:
    from NanoVNA_UTN_Toolkit.shared.utils.load_resource import load_resource
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

class JsonResourceLoader:

    def __init__(self, self_window, module = "material_characterization", lang="en", json_resource = "characterization_methods"):

        self.window = self_window
        self.module = module
        self.lang = lang
        self.json_resource = json_resource

    def _load_json(self):

        return load_resource(
            self.module,
            self.lang,
            self.json_resource
        )

# ------------------------------------------------------------------------------------------------------------------- #
# Main Menu
# ------------------------------------------------------------------------------------------------------------------- #

    def load_main_menu_resources(self):

        raw_data = self._load_json()

        ui_data = raw_data.get("main_menu_ui", {})

        header = ui_data.get("header", {})
        modules = ui_data.get("modules", {})

        dut_measurement = modules.get("dut_measurement", {})
        materials_characterization = modules.get("materials_characterization", {})

        self.window.menu_title = header.get("title", "")
        self.window.menu_description = header.get("description", "")

        self.window.dut_measurement_title = dut_measurement.get("title", "")
        self.window.dut_measurement_description = dut_measurement.get("description", "")

        self.window.materials_characterization_title = materials_characterization.get("title", "")
        self.window.materials_characterization_description = materials_characterization.get("description", "")
    
# ------------------------------------------------------------------------------------------------------------------- #
# DUT Measurement Module
# ------------------------------------------------------------------------------------------------------------------- #

    def load_dut_measurement_welcome_resources(self):

        raw_data = self._load_json()

        ui_data = raw_data.get("dut_measurement_ui", {})

        module_overview = ui_data.get("module_overview", {})
        kit_section = ui_data.get("kit_section", {})

        self.window.dut_welcome_ui_calibration_title = module_overview.get("title", "")
        self.window.dut_welcome_ui_label_calibration_button = module_overview.get("label_calibration_button")
        self.window.dut_welcome_ui_descriptions = "".join(module_overview.get("description", []))

        self.window.dut_welcome_ui_kit_title = kit_section.get("title", "")
        self.window.dut_welcome_ui_kit_selection_title = kit_section.get("kit_selection_title", "")
        self.window.dut_welcome_ui_description_kit = kit_section.get("description_kit", "")
        self.window.dut_welcome_ui_no_kit_selected = kit_section.get("no_kit_selected", "")
        self.window.dut_welcome_ui_label_kit_button = kit_section.get("label_kit_button", "")
        self.window.dut_welcome_ui_import_section_title = kit_section.get("import_section_title", "")
        self.window.dut_welcome_ui_import_description = kit_section.get("import_description", "")
        self.window.dut_welcome_ui_import_button_text = kit_section.get("import_button", "")


    def load_dut_measurement_wizard_resources(self):

        raw_data = self._load_json()

        ui_data = raw_data.get("dut_measurement_wizard_ui", {})

        intro_screen = ui_data.get("intro_screen", {})
        steps_section = ui_data.get("steps", {})

        calibration_section = intro_screen.get("calibration_method_section", {})
        sweep_section = intro_screen.get("sweep_section", {})

        # ---------------------------------------------------------------- #
        # Method Selector Screen
        # ---------------------------------------------------------------- #

        self.window.dut_wizard_ui_title = calibration_section.get("title", "")
        self.window.dut_wizard_ui_label_method_selection = calibration_section.get("label_calibration_method_selection", "")
        self.window.dut_wizard_ui_descriptions = "".join(calibration_section.get("description", []))

        self.window.dut_wizard_ui_osm = calibration_section.get("method_osm")
        self.window.dut_wizard_ui_normalization_open = calibration_section.get("method_normalization_open")
        self.window.dut_wizard_ui_normalization_short = calibration_section.get("method_normalization_short")
        self.window.dut_wizard_ui_normalization_thru = calibration_section.get("method_normalization_thru")
        self.window.dut_wizard_ui_1_port = calibration_section.get("method_1_port")
        self.window.dut_wizard_ui_E_R = calibration_section.get("method_E_R")

        self.window.dut_wizard_ui_sweep_title = sweep_section.get("title", "")
        self.window.dut_wizard_ui_start_freq = sweep_section.get("start_frec", "")
        self.window.dut_wizard_ui_stop_freq = sweep_section.get("stop_frec", "")
        self.window.dut_wizard_ui_steps = sweep_section.get("steps", "")

        # ---------------------------------------------------------------- #
        # Steps Screen
        # ---------------------------------------------------------------- #

        self.window.dut_wizard_ui_steps_title = steps_section.get("steps_title", "")
        self.window.dut_wizard_ui_instruction_text = steps_section.get("instruction_text", "")
        self.window.dut_wizard_ui_measure_label_button = steps_section.get("measure_label_button", "")
        self.window.dut_wizard_ui_re_measure_label_button = steps_section.get("re-measure_label_button", "")
        self.window.dut_wizard_ui_label_measure = steps_section.get("label_measure", "")
        self.window.dut_wizard_ui_calibration_status = steps_section.get("calibration_status", "")
        self.window.dut_wizard_ui_label_save_cal = steps_section.get("label_save_cal", "")
        self.window.dut_wizard_ui_label_finish_button = steps_section.get("label_finish_button", "")

    def load_measurement_graphics_resources(self):

        raw_data = self._load_json()

        ui_data = raw_data.get("measurement_graphics_ui", {})

        menu_bar = ui_data.get("menu_bar", {})
        top_bar = ui_data.get("top_bar", {})
        plots = ui_data.get("plots", {})
        s_parameter_details = ui_data.get("s_parameter_details", {})
        dut_parameters = ui_data.get("dut_parameters", {})
        status_messages = ui_data.get("status_messages", {})
        marker_diff = ui_data.get("marker_diff", {})

        calibration_status = top_bar.get("calibration_status", {})

        # ---------------------------------------------------------------- #
        # Menu Bar
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_menu_file = menu_bar.get("file", "")
        self.window.measurement_ui_menu_edit = menu_bar.get("edit", "")
        self.window.measurement_ui_menu_view = menu_bar.get("view", "")
        self.window.measurement_ui_menu_sweep = menu_bar.get("sweep", "")
        self.window.measurement_ui_menu_calibration = menu_bar.get("calibration", "")
        self.window.measurement_ui_menu_help = menu_bar.get("help", "")

        # ---------------------------------------------------------------- #
        # Top Bar
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_button_connect = top_bar.get("button_connect", "")
        self.window.measurement_ui_button_reconnect = top_bar.get("button_reconnect", "")
        self.window.measurement_ui_button_disconnect = top_bar.get("button_disconnect", "")
        self.window.measurement_ui_button_run_sweep = top_bar.get("button_run_sweep", "")
        self.window.measurement_ui_button_stop_sweep = top_bar.get("button_stop_sweep", "")

        self.window.measurement_ui_sweep_info = top_bar.get("sweep_info", "")

        self.window.measurement_ui_no_calibration = calibration_status.get("no_calibration", "")
        self.window.measurement_ui_wizard_calibration = calibration_status.get("wizard_calibration", "")
        self.window.measurement_ui_calibration_kit = calibration_status.get("calibration_kit", "")
        self.window.measurement_ui_imported_dut = calibration_status.get("imported_dut", "")

        # ---------------------------------------------------------------- #
        # Magnitude and Phase Plot
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_magnitude_title = plots.get("title_mag", "")
        self.window.measurement_ui_phase_title = plots.get("title_phase", "")
        self.window.measurement_ui_magnitude_waiting_text = plots.get("waiting_text", "")
        self.window.measurement_ui_magnitude_x_axis = plots.get("x_axis", "")
        self.window.measurement_ui_magnitude_y_axis = plots.get("y_axis", "")

        # ---------------------------------------------------------------- #
        # S-Parameter Details
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_s_parameter_details_title = s_parameter_details.get("title", "")

        self.window.measurement_ui_s_parameter_frequency = s_parameter_details.get("frequency", "")
        self.window.measurement_ui_s_parameter_s11_complex = s_parameter_details.get("s11_complex", "")
        self.window.measurement_ui_s_parameter_s21_complex = s_parameter_details.get("s21_complex", "")

        self.window.measurement_ui_s_parameter_magnitude_s11 = s_parameter_details.get("magnitude_s11", "")
        self.window.measurement_ui_s_parameter_magnitude_s21 = s_parameter_details.get("magnitude_s21", "")

        self.window.measurement_ui_s_parameter_phase = s_parameter_details.get("phase", "")

        # ---------------------------------------------------------------- #
        # DUT Parameters
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_dut_parameters_title = dut_parameters.get("title", "")

        self.window.measurement_ui_dut_zin = dut_parameters.get("zin", "")
        self.window.measurement_ui_dut_return_loss = dut_parameters.get("return_loss", "")
        self.window.measurement_ui_dut_insertion_loss = dut_parameters.get("insertion_loss", "")
        self.window.measurement_ui_dut_vswr = dut_parameters.get("vswr", "")
        self.window.measurement_ui_dut_group_delay = dut_parameters.get("group_delay", "")

        # ---------------------------------------------------------------- #
        # Status Messages
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_waiting_for_connection = status_messages.get("waiting_for_connection", "")
        self.window.measurement_ui_device_connected = status_messages.get("device_connected", "")
        self.window.measurement_ui_device_disconnected = status_messages.get("device_disconnected", "")

        self.window.measurement_ui_waiting_for_sweep = status_messages.get("waiting_for_sweep", "")
        self.window.measurement_ui_running_sweep = status_messages.get("running_sweep", "")
        self.window.measurement_ui_sweep_completed = status_messages.get("sweep_completed", "")

        self.window.measurement_ui_calibration_loaded = status_messages.get("calibration_loaded", "")
        self.window.measurement_ui_calibration_saved = status_messages.get("calibration_saved", "")
        self.window.measurement_ui_calibration_cleared = status_messages.get("calibration_cleared", "")

        self.window.measurement_ui_importing_dut = status_messages.get("importing_dut", "")
        self.window.measurement_ui_dut_loaded = status_messages.get("dut_loaded", "")

        # ---------------------------------------------------------------- #
        # Markers Difference
        # ---------------------------------------------------------------- #

        self.window.measurement_ui_marker_diff = marker_diff.get("label_diff", "")

# ------------------------------------------------------------------------------------------------------------------- #
# Material Characterization Module
# ------------------------------------------------------------------------------------------------------------------- #

    def load_characterization_welcome_resources(self):

        raw_data = self._load_json()

        ui_data = raw_data.get("material_characterization_ui", {})

        module_overview = ui_data.get("module_overview", {})
        characterization_section = ui_data.get("characterization_section", {})

        self.window.charac_welcome_ui_module_overview_title = module_overview.get("title", "")
        self.window.charac_welcome_ui_descriptions = module_overview.get("description", [])

        self.window.charac_welcome_ui_characterization_title = characterization_section.get("title", "")
        self.window.charac_welcome_ui_method_selection_title = characterization_section.get("method_selection_title", "")
        self.window.charac_welcome_ui_no_characterization_selected = characterization_section.get("no_method_selected", "")
        self.window.charac_welcome_ui_open_methods_button = characterization_section.get("open_methods_button", "")
        self.window.charac_welcome_ui_import_section_title = characterization_section.get("import_section_title", "")
        self.window.charac_welcome_ui_import_description = characterization_section.get("import_description", "")
        self.window.charac_welcome_ui_import_button_text = characterization_section.get("import_button", "")

    def load_characterization_method_resources(self):

        raw_data = self._load_json()

        self.window.charac_wizard_ui_method_title = raw_data.get("title", "")
        self.window.charac_wizard_ui_method_select_label = raw_data.get("select_label", "")
        self.window.charac_wizard_ui_method_dropdown_placeholder = raw_data.get("dropdown_placeholder", "")
        self.window.charac_wizard_ui_method_label_description = raw_data.get("label_description", "")
        self.window.charac_wizard_ui_method_empty_description = raw_data.get("empty_description", "")

        return raw_data.get("methods", {})


