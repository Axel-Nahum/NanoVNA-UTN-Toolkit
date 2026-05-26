try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.load_resource import load_resource
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
# Shared Resources
# ------------------------------------------------------------------------------------------------------------------- #

    def load_connection_resources(self):

        raw_data = self._load_json()

        connection_status = raw_data.get("status", {})
        serial_status = raw_data.get("serialStatus", {})
        device_information = raw_data.get("deviceInformation", {})

        fields = device_information.get("fields", {})
        board_field = fields.get("board", {})
        version_field = fields.get("version", {})
        device_type = fields.get("deviceType", {})
        serial_number = fields.get("serialNumber", {})
        platform = fields.get("platform", {})
        architecture = fields.get("architecture", {})
        built_time = fields.get("buildTime", {})
        parameters = fields.get("parameters", {})
        features = fields.get("features", {})

        button_labels = raw_data.get("buttons", {})
        refresh_button = button_labels.get("refresh", "")
        disconnect_button = button_labels.get("disconnect", "")
        clear_button = button_labels.get("clearLog", "")
        stop_button = button_labels.get("stop", "")
        open_menu_button = button_labels.get("openMenu", "")

        # --------------------------------------------------------------------------------------------------------------- #
        # Connection Status
        # --------------------------------------------------------------------------------------------------------------- #

        self.window.connection_status_connected = connection_status.get("connected", "")
        self.window.connection_status_starting = connection_status.get("starting", "")
        self.window.connection_status_disconnected = connection_status.get("disconnected", "")

        self.window.no_interfaces_message = serial_status.get("noInterfaces", "")
        self.window.searching_interfaces_message = serial_status.get("searchingInterfaces", "")
        self.window.testing_interfaces_message = serial_status.get("testingInterfaces", "")
        self.window.reading_device_info_message = serial_status.get("readingDeviceInfo", "")
        self.window.reading_device_capabilities_message = serial_status.get("readingDeviceCapabilities", "")
        self.window.device_connected_message = serial_status.get("deviceConnected", "")

        # --------------------------------------------------------------------------------------------------------------- #
        # Device Information Title
        # --------------------------------------------------------------------------------------------------------------- #

        self.window.device_info_title = device_information.get("title", "")

        # ------------------------------------------------------------------------------------------------------------------- #
        # Device Information
        # ------------------------------------------------------------------------------------------------------------------- #

        self.window.device_info_board_label = board_field.get("label", "")
        self.window.device_info_board_value = board_field.get("value", "")

        self.window.device_info_version_label = version_field.get("label", "")
        self.window.device_info_version_value = version_field.get("value", "")

        self.window.device_info_type_label = device_type.get("label", "")
        self.window.device_info_type_value = device_type.get("value", "")

        self.window.device_info_serial_label = serial_number.get("label", "")
        self.window.device_info_serial_value = serial_number.get("value", "")

        self.window.device_info_platform_label = platform.get("label", "")
        self.window.device_info_platform_value = platform.get("value", "")

        self.window.device_info_architecture_label = architecture.get("label", "")
        self.window.device_info_architecture_value = architecture.get("value", "")

        self.window.device_info_built_time_label = built_time.get("label", "")
        self.window.device_info_built_time_value = built_time.get("value", "")

        self.window.device_info_parameters_label = parameters.get("label", "")
        self.window.device_info_parameters_value = parameters.get("value", "")

        self.window.device_info_features_label = features.get("label", "")
        self.window.device_info_features_value = features.get("value", "")

        # ------------------------------------------------------------------------------------------------------------------- #
        # Buttons
        # ------------------------------------------------------------------------------------------------------------------- #

        self.window.refresh_button_label = refresh_button
        self.window.disconnect_button_label = disconnect_button
        self.window.clear_log_button_label = clear_button
        self.window.stop_button_label = stop_button
        self.window.open_menu_button_label = open_menu_button

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

        self.window.measurement_ui_magnitude_title = plots.get("title_mag", "soy goy")
        self.window.measurement_ui_phase_title = plots.get("title_phase", "goy sere")
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

    def load_measurement_menu_resources(self):

        raw_data = self._load_json()

        menu_data = raw_data.get("menu", {})

        file_menu = menu_data.get("file_menu", {})
        edit_menu = menu_data.get("edit_menu", {})
        view_menu = menu_data.get("view_menu", {})
        sweep_menu = menu_data.get("sweep_menu", {})
        calibration_menu = menu_data.get("calibration_menu", {})
        help_menu = menu_data.get("help_menu", {})

        # ---------------------------------------------------------------- #
        # File Menu
        # ---------------------------------------------------------------- #

        self.window.measurement_menu_import_touchstone_cal = file_menu.get("import_touchstone_cal", "")
        self.window.measurement_menu_import_touchstone_dut = file_menu.get("import_touchstone_dut", "")
        self.window.measurement_menu_export_pdf = file_menu.get("export_PDF", "")
        self.window.measurement_menu_export_touchstone = file_menu.get("export_touchstone", "")
        self.window.measurement_menu_export_errors = file_menu.get("export_errors", "")
        self.window.measurement_menu_back_to_menu = file_menu.get("back_to_menu", "")

        # ---------------------------------------------------------------- #
        # Edit Menu
        # ---------------------------------------------------------------- #

        self.window.measurement_menu_graphics_markers = edit_menu.get("graphics_markers", "")

        # ---------------------------------------------------------------- #
        # View Menu
        # ---------------------------------------------------------------- #

        self.window.measurement_menu_graphics = view_menu.get("graphics", "")

        # ---------------------------------------------------------------- #
        # Sweep Menu
        # ---------------------------------------------------------------- #

        self.window.measurement_menu_sweep_option = sweep_menu.get("option", "")
        self.window.measurement_menu_run_sweep = sweep_menu.get("run_sweep", "")

        # ---------------------------------------------------------------- #
        # Calibration Menu
        # ---------------------------------------------------------------- #

        self.window.measurement_menu_cal_wizard = calibration_menu.get("cal_wizard", "")
        self.window.measurement_menu_no_calibration = calibration_menu.get("no_calibration", "")
        self.window.measurement_menu_select_kit = calibration_menu.get("select_kit", "")
        self.window.measurement_menu_save_kit = calibration_menu.get("save_kit", "")
        self.window.measurement_menu_delete_kit = calibration_menu.get("delete_kit", "")

        # ---------------------------------------------------------------- #
        # Help Menu
        # ---------------------------------------------------------------- #

        self.window.measurement_menu_report = help_menu.get("report", "")
        self.window.measurement_menu_about_en = help_menu.get("import Touchstone_dut", "")
        self.window.measurement_menu_about_es = help_menu.get("export_PDF", "")

    def load_view_edit_ui_resources(self):

        raw_data = self._load_json()

        graphic_view = raw_data.get("graphic_view", {})
        edit_graphics = raw_data.get("edit_graphics", {})

        # ---------------------------------------------------------------- #
        # Graphic View
        # ---------------------------------------------------------------- #

        self.window.graphic_view_window_title = graphic_view.get("window_title", "")

        tabs = graphic_view.get("tabs", {})
        self.window.graphic_view_tab_graphic_1 = tabs.get("graphic_1", "")
        self.window.graphic_view_tab_graphic_2 = tabs.get("graphic_2", "")

        groups = graphic_view.get("groups", {})
        self.window.graphic_view_group_select_parameter = groups.get("select_parameter", "")
        self.window.graphic_view_group_selector_graphic_1 = groups.get("selector_graphic_1", "")
        self.window.graphic_view_group_selector_graphic_2 = groups.get("selector_graphic_2", "")

        parameters = graphic_view.get("parameters", {})
        self.window.graphic_view_param_s11 = parameters.get("s11", "")
        self.window.graphic_view_param_s21 = parameters.get("s21", "")

        graph_types = graphic_view.get("graph_types", {})
        self.window.graphic_view_smith_diagram = graph_types.get("smith_diagram", "")
        self.window.graphic_view_magnitude = graph_types.get("magnitude", "")
        self.window.graphic_view_phase = graph_types.get("phase", "")

        buttons = graphic_view.get("buttons", {})
        self.window.graphic_view_cancel = buttons.get("cancel", "")
        self.window.graphic_view_apply = buttons.get("apply", "")

        graphic_1 = graphic_view.get("graphic_1", {})
        graphic_2 = graphic_view.get("graphic_2", {})

        g1_mag = graphic_1.get("magnitude", {})
        g1_phase = graphic_1.get("phase", {})
        g1_smith = graphic_1.get("smith_diagram", {})

        self.window.graphic_view_g1_mag_x_axis = g1_mag.get("x_axis", "")
        self.window.graphic_view_g1_mag_y_s11 = g1_mag.get("y_axis_s11", "")
        self.window.graphic_view_g1_mag_y_s21 = g1_mag.get("y_axis_s21", "")

        self.window.graphic_view_g1_phase_x_axis = g1_phase.get("x_axis", "")
        self.window.graphic_view_g1_phase_y_s11 = g1_phase.get("y_axis_s11", "")
        self.window.graphic_view_g1_phase_y_s21 = g1_phase.get("y_axis_s21", "")

        self.window.graphic_view_g1_smith_real = g1_smith.get("real_axis", "")
        self.window.graphic_view_g1_smith_imag = g1_smith.get("imaginary_axis", "")

        g2_mag = graphic_2.get("magnitude", {})
        g2_phase = graphic_2.get("phase", {})
        g2_smith = graphic_2.get("smith_diagram", {})

        self.window.graphic_view_g2_mag_x_axis = g2_mag.get("x_axis", "")
        self.window.graphic_view_g2_mag_y_s11 = g2_mag.get("y_axis_s11", "")
        self.window.graphic_view_g2_mag_y_s21 = g2_mag.get("y_axis_s21", "")

        self.window.graphic_view_g2_phase_x_axis = g2_phase.get("x_axis", "")
        self.window.graphic_view_g2_phase_y_s11 = g2_phase.get("y_axis_s11", "")
        self.window.graphic_view_g2_phase_y_s21 = g2_phase.get("y_axis_s21", "")

        self.window.graphic_view_g2_smith_real = g2_smith.get("real_axis", "")
        self.window.graphic_view_g2_smith_imag = g2_smith.get("imaginary_axis", "")

        # ---------------------------------------------------------------- #
        # Edit Graphics
        # ---------------------------------------------------------------- #

        self.window.edit_graphics_window_title = edit_graphics.get("window_title", "")

        tabs = edit_graphics.get("tabs", {})
        self.window.edit_graphics_tab_graphic_1 = tabs.get("graphic_1", "")
        self.window.edit_graphics_tab_graphic_2 = tabs.get("graphic_2", "")

        groups = edit_graphics.get("groups", {})
        self.window.edit_graphics_group_trace = groups.get("edit_trace", "")
        self.window.edit_graphics_group_markers = groups.get("edit_markers", "")
        self.window.edit_graphics_group_graphics = groups.get("edit_graphics", "")

        trace = edit_graphics.get("trace", {})
        self.window.edit_graphics_trace_color = trace.get("trace_color", "")
        self.window.edit_graphics_trace_width = trace.get("trace_width", "")

        markers = edit_graphics.get("markers", {})
        self.window.edit_graphics_marker1_color = markers.get("marker_1_color", "")
        self.window.edit_graphics_marker2_color = markers.get("marker_2_color", "")
        self.window.edit_graphics_marker1_size = markers.get("marker_1_size", "")
        self.window.edit_graphics_marker2_size = markers.get("marker_2_size", "")

        graphics = edit_graphics.get("graphics", {})
        self.window.edit_graphics_background_color = graphics.get("background_color", "")
        self.window.edit_graphics_text_color = graphics.get("text_color", "")
        self.window.edit_graphics_axis_color = graphics.get("axis_color", "")

        buttons = edit_graphics.get("buttons", {})
        self.window.edit_graphics_cancel = buttons.get("cancel", "")
        self.window.edit_graphics_apply = buttons.get("apply", "")

        eg_g1 = edit_graphics.get("graphic_1", {})
        eg_g2 = edit_graphics.get("graphic_2", {})

        eg_g1_mag = eg_g1.get("magnitude", {})
        eg_g1_phase = eg_g1.get("phase", {})

        self.window.edit_graphics_g1_mag_x_axis = eg_g1_mag.get("x_axis", "")
        self.window.edit_graphics_g1_mag_y_s11 = eg_g1_mag.get("y_axis_s11", "")
        self.window.edit_graphics_g1_mag_y_s21 = eg_g1_mag.get("y_axis_s21", "")
        self.window.edit_graphics_g1_mag_title = eg_g1_mag.get("title_mag", "")

        self.window.edit_graphics_g1_phase_x_axis = eg_g1_phase.get("x_axis", "")
        self.window.edit_graphics_g1_phase_y_s11 = eg_g1_phase.get("y_axis_s11", "")
        self.window.edit_graphics_g1_phase_y_s21 = eg_g1_phase.get("y_axis_s21", "")
        self.window.edit_graphics_g1_phase_title = eg_g1_mag.get("title_phase", "")

        eg_g2_mag = eg_g2.get("magnitude", {})
        eg_g2_phase = eg_g2.get("phase", {})

        self.window.edit_graphics_g2_mag_x_axis = eg_g2_mag.get("x_axis", "")
        self.window.edit_graphics_g2_mag_y_s11 = eg_g2_mag.get("y_axis_s11", "")
        self.window.edit_graphics_g2_mag_y_s21 = eg_g2_mag.get("y_axis_s21", "")
        self.window.edit_graphics_g2_mag_title = eg_g2_mag.get("title_mag", "")

        self.window.edit_graphics_g2_phase_x_axis = eg_g2_phase.get("x_axis", "")
        self.window.edit_graphics_g2_phase_y_s11 = eg_g2_phase.get("y_axis_s11", "")
        self.window.edit_graphics_g2_phase_y_s21 = eg_g2_phase.get("y_axis_s21", "")
        self.window.edit_graphics_g2_phase_title = eg_g2_mag.get("title_phase", "")

    def load_pdf_export_resources(self):

        raw_data = self._load_json()

        pdf_export = raw_data.get("pdf_export", {})

        latex_pdf_export_setup = pdf_export.get("latex_pdf_export_setup", {})
        graph_preview = pdf_export.get("graph_preview", {})

        compiler_status_group = latex_pdf_export_setup.get("compiler_status_group", {})
        output_location_group = latex_pdf_export_setup.get("output_location_group", {})
        setup_buttons = latex_pdf_export_setup.get("buttons", {})

        top_messages = graph_preview.get("top_messages", {})
        navigation_buttons = graph_preview.get("navigation_buttons", {})
        markers = graph_preview.get("markers", {})
        preview_buttons = graph_preview.get("buttons", {})
        plots = graph_preview.get("plots", {})

        s11_smith = plots.get("s11_smith", {})
        s11_magnitude = plots.get("s11_magnitude", {})
        s11_phase = plots.get("s11_phase", {})
        s21_magnitude = plots.get("s21_magnitude", {})
        s21_phase = plots.get("s21_phase", {})

        # ---------------------------------------------------------------- #
        # LaTeX PDF Export Setup
        # ---------------------------------------------------------------- #

        self.window.pdf_export_window_title = latex_pdf_export_setup.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Compiler Status Group
        # ---------------------------------------------------------------- #

        self.window.pdf_export_compiler_group_title = compiler_status_group.get("title", "")

        self.window.pdf_export_checking_installation = compiler_status_group.get("checking_installation", "")
        self.window.pdf_export_scanning_system = compiler_status_group.get("scanning_system", "")

        self.window.pdf_export_compiler_available = compiler_status_group.get("compiler_available", "")
        self.window.pdf_export_compiler_not_found = compiler_status_group.get("compiler_not_found", "")

        self.window.pdf_export_found_working_compiler = compiler_status_group.get("found_working_compiler", "")
        self.window.pdf_export_manual_select_compiler = compiler_status_group.get("manual_select_compiler", "")

        self.window.pdf_export_browse_compiler_button = compiler_status_group.get("browse_compiler_button", "")

        # ---------------------------------------------------------------- #
        # Output Location Group
        # ---------------------------------------------------------------- #

        self.window.pdf_export_output_group_title = output_location_group.get("title", "")

        self.window.pdf_export_select_output_placeholder = output_location_group.get("select_output_placeholder", "")
        self.window.pdf_export_browse_button = output_location_group.get("browse_button", "")

        self.window.pdf_export_output_hint = output_location_group.get("output_hint", "")

        # ---------------------------------------------------------------- #
        # Setup Buttons
        # ---------------------------------------------------------------- #

        self.window.pdf_export_cancel_button = setup_buttons.get("cancel", "")
        self.window.pdf_export_disabled_button = setup_buttons.get("export_disabled", "")
        self.window.pdf_export_export_button = setup_buttons.get("export", "")

        # ---------------------------------------------------------------- #
        # Graph Preview
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_window_title = graph_preview.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Top Messages
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_ready = top_messages.get("preview_ready", "")
        self.window.pdf_preview_instruction = top_messages.get("preview_instruction", "")

        # ---------------------------------------------------------------- #
        # Navigation Buttons
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_previous = navigation_buttons.get("previous", "")
        self.window.pdf_preview_next = navigation_buttons.get("next", "")

        # ---------------------------------------------------------------- #
        # Markers
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_marker_1 = markers.get("marker_1", "")
        self.window.pdf_preview_marker_2 = markers.get("marker_2", "")

        self.window.pdf_preview_frequency_unit = markers.get("frequency_unit", "")

        # ---------------------------------------------------------------- #
        # Preview Buttons
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_generate_report = preview_buttons.get("generate_report", "")

        # ---------------------------------------------------------------- #
        # S11 Smith
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_s11_smith_title = s11_smith.get("title", "")

        # ---------------------------------------------------------------- #
        # S11 Magnitude
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_s11_magnitude_title = s11_magnitude.get("title", "")
        self.window.pdf_preview_s11_magnitude_x_axis = s11_magnitude.get("x_axis", "")
        self.window.pdf_preview_s11_magnitude_y_axis = s11_magnitude.get("y_axis", "")

        # ---------------------------------------------------------------- #
        # S11 Phase
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_s11_phase_title = s11_phase.get("title", "")
        self.window.pdf_preview_s11_phase_x_axis = s11_phase.get("x_axis", "")
        self.window.pdf_preview_s11_phase_y_axis = s11_phase.get("y_axis", "")

        # ---------------------------------------------------------------- #
        # S21 Magnitude
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_s21_magnitude_title = s21_magnitude.get("title", "")
        self.window.pdf_preview_s21_magnitude_x_axis = s21_magnitude.get("x_axis", "")
        self.window.pdf_preview_s21_magnitude_y_axis = s21_magnitude.get("y_axis", "")

        # ---------------------------------------------------------------- #
        # S21 Phase
        # ---------------------------------------------------------------- #

        self.window.pdf_preview_s21_phase_title = s21_phase.get("title", "")
        self.window.pdf_preview_s21_phase_x_axis = s21_phase.get("x_axis", "")
        self.window.pdf_preview_s21_phase_y_axis = s21_phase.get("y_axis", "")

    def load_export_touchstone_resources(self):

        raw_data = self._load_json()

        export_touchstone = raw_data.get("export_touchstone", {})

        buttons_labels = export_touchstone.get("buttons", {})
        options_sxp = export_touchstone.get("options_sxp", {})

        # ---------------------------------------------------------------- #
        # Export Touchstone Setup
        # ---------------------------------------------------------------- #

        self.window.export_touchstone_window_title = export_touchstone.get("window_title", "")
        self.window.export_touchstone_export_title = export_touchstone.get("export_title", "")

        # ---------------------------------------------------------------- #
        # Setup Buttons
        # ---------------------------------------------------------------- #

        self.window.export_touchstone_cancel_button = buttons_labels.get("cancel", "")
        self.window.export_touchstone_export_button = buttons_labels.get("export", "")

        # ---------------------------------------------------------------- #
        # Options for .sxp
        # ---------------------------------------------------------------- #

        self.window.export_touchstone_s1p_option = options_sxp.get("s1p", "")
        self.window.export_touchstone_s2p_option = options_sxp.get("s2p", "")
        self.window.export_touchstone_info = options_sxp.get("info", "")

    def load_exporters_resources(self):

        raw_data = self._load_json()

        exporters = raw_data.get("exporters", {})

        exporters_preview = exporters.get("exporters_preview", {})
        buttons = exporters.get("buttons", {})

        # ---------------------------------------------------------------- #
        # Exporters Window
        # ---------------------------------------------------------------- #

        self.window.exporters_window_title = exporters.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Exporters Preview
        # ---------------------------------------------------------------- #

        self.window.exporters_preview_title = exporters_preview.get("title", "")

        # ---------------------------------------------------------------- #
        # Buttons
        # ---------------------------------------------------------------- #

        self.window.exporters_copy_button = buttons.get("copy", "")
        self.window.exporters_image_button = buttons.get("image", "")
        self.window.exporters_csv_button = buttons.get("CSV", "")
        self.window.exporters_close_button = buttons.get("close", "")

    def load_set_range_resources(self):

        raw_data = self._load_json()

        set_range = raw_data.get("set_range", {})

        range_y = set_range.get("range_y", {})
        buttons = set_range.get("buttons", {})

        # ---------------------------------------------------------------- #
        # Set Range Window
        # ---------------------------------------------------------------- #

        self.window.set_range_window_title = set_range.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Set Range Y
        # ---------------------------------------------------------------- #

        self.window.set_range_y_min = range_y.get("y_min", "")
        self.window.set_range_y_max = range_y.get("y_max", "")

        # ---------------------------------------------------------------- #
        # Buttons
        # ---------------------------------------------------------------- #

        self.window.set_range_apply = buttons.get("apply", "")
        self.window.set_range_close = buttons.get("close", "")

    def load_cal_kits_resources(self):

        raw_data = self._load_json()

        calibration_kits = raw_data.get("calibration_kits", {})

        select_kit = calibration_kits.get("select_kit", {})
        save_kit = calibration_kits.get("save_kit", {})
        delete_kit = calibration_kits.get("delete_kit", {})

        buttons_select = select_kit.get("buttons", {})
        buttons_save = save_kit.get("buttons", {})
        buttons_delete = delete_kit.get("buttons", {})

        # ---------------------------------------------------------------- #
        # Select Kit Window
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_title_select = select_kit.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Select Text
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_select_text = select_kit.get("select_text", "")

        # ---------------------------------------------------------------- #
        # Buttons
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_cancel = buttons_select.get("cancel", "")
        self.window.cal_kit_window_select = buttons_select.get("select", "")

        # ---------------------------------------------------------------- #
        # Delete Kit Window
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_title_delete = delete_kit.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Delete Text
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_delete_text = delete_kit.get("delete_text", "")

        # ---------------------------------------------------------------- #
        # Buttons
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_cancel = buttons_delete.get("cancel", "")
        self.window.cal_kit_window_delete = buttons_delete.get("delete", "")

        # ---------------------------------------------------------------- #
        # Save Kit Window
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_title_save = save_kit.get("window_title", "")

        # ---------------------------------------------------------------- #
        # Save Text
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_save_text = save_kit.get("save_text", "")

        # ---------------------------------------------------------------- #
        # Buttons
        # ---------------------------------------------------------------- #

        self.window.cal_kit_window_cancel = buttons_save.get("cancel", "")
        self.window.cal_kit_window_save = buttons_save.get("save", "")

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


