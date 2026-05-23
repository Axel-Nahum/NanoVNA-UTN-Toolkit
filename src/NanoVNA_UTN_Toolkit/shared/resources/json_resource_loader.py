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

        self.window.module_overview_title = module_overview.get("title", "")
        self.window.label_calibration_button = module_overview.get("label_calibration_button")
        self.window.descriptions = "".join(module_overview.get("description", []))

        self.window.kit_title = kit_section.get("title", "")
        self.window.kit_selection_title = kit_section.get("kit_selection_title", "")
        self.window.no_kit_selected = kit_section.get("no_kit_selected", "")
        self.window.label_kit_button = kit_section.get("label_kit_button", "")
        self.window.import_section_title = kit_section.get("import_section_title", "")
        self.window.import_description = kit_section.get("import_description", "")
        self.window.import_button_text = kit_section.get("import_button", "")
    
# ------------------------------------------------------------------------------------------------------------------- #
# Material Characterization Module
# ------------------------------------------------------------------------------------------------------------------- #

    def load_characterization_welcome_resources(self):

        raw_data = self._load_json()

        ui_data = raw_data.get("material_characterization_ui", {})

        module_overview = ui_data.get("module_overview", {})
        characterization_section = ui_data.get("characterization_section", {})

        self.window.module_overview_title = module_overview.get("title", "")
        self.window.descriptions = module_overview.get("description", [])

        self.window.characterization_title = characterization_section.get("title", "")
        self.window.method_selection_title = characterization_section.get("method_selection_title", "")
        self.window.no_characterization_selected = characterization_section.get("no_method_selected", "")
        self.window.open_methods_button = characterization_section.get("open_methods_button", "")
        self.window.import_section_title = characterization_section.get("import_section_title", "")
        self.window.import_description = characterization_section.get("import_description", "")
        self.window.import_button_text = characterization_section.get("import_button", "")

    def load_characterization_method_resources(self):

        raw_data = self._load_json()

        self.window.method_ui_title = raw_data.get("title", "")
        self.window.method_ui_select_label = raw_data.get("select_label", "")
        self.window.method_ui_dropdown_placeholder = raw_data.get("dropdown_placeholder", "")
        self.window.method_ui_label_description = raw_data.get("label_description", "")
        self.window.method_ui_empty_description = raw_data.get("empty_description", "")

        return raw_data.get("methods", {})


