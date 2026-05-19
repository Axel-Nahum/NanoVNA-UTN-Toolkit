from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.measurement_main_window import MeasurementMainWindow

def build_method_a_result(self):
    self.measurement_window = MeasurementMainWindow(vna_device=self.vna_device, wizard_window=self)

    self.measurement_window.show()

    self.close()