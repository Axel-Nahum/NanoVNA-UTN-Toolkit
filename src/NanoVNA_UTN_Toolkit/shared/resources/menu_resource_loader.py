from NanoVNA_UTN_Toolkit.utils import safe_import
load_resource = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.load_resource", "load_resource")


class MenuResourceLoader:

    def __init__(self, self_window, module="menu_resource", lang="en", json_resource="menu"):
        self.window = self_window
        self.module = module
        self.lang = lang
        self.json_resource = json_resource

    def _load_json(self):
        return load_resource(self.module, self.lang, self.json_resource)

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
