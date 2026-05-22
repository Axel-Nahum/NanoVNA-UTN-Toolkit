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
# DUT Measurement Module
# ------------------------------------------------------------------------------------------------------------------- #
    
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
        self.window.no_calibration_selected = characterization_section.get("no_calibration_selected", "")
        self.window.open_methods_button = characterization_section.get("open_methods_button", "")
        self.window.import_section_title = characterization_section.get("import_section_title", "")
        self.window.import_description = characterization_section.get("import_description", "")
        self.window.import_button_text = characterization_section.get("import_button", "")

    def load_characterization_method_resources(self):

        raw_data = self._load_json()

        return raw_data.get("methods", {})


