from NanoVNA_UTN_Toolkit.utils import safe_import
load_resource = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.load_resource", "load_resource")


class CharacterizationResourceLoader:

    def __init__(self, self_window, module="material_characterization", lang="en", json_resource="characterization_methods"):
        self.window = self_window
        self.module = module
        self.lang = lang
        self.json_resource = json_resource

    def _load_json(self):
        return load_resource(self.module, self.lang, self.json_resource)

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
