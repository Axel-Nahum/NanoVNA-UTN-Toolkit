"""
Enhanced calibration manager module for NanoVNA-UTN-Toolkit.
Handles OSM calibrations with persistent state and Touchstone export.
"""
import logging
import os
import sys
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import skrf as rf

from pathlib import Path

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

class OSMCalibrationManager:
    """
    Enhanced OSM calibration manager with persistent state and Touchstone export.
    """
    
    def __init__(self, base_path: str = None):
        
        self.osm_results_path = get_calibration_path(
            "modules/dut_measurement/calibration/osm_results",
            "modules/dut_measurement/calibration/osm_results",
            Path(__file__).resolve()
        )

        self.thru_results_path = get_calibration_path(
            "modules/dut_measurement/calibration/thru_results",
            "modules/dut_measurement/calibration/thru_results",
            Path(__file__).resolve()
        )

        self.kits_path = self.thru_results_path = get_calibration_path(
            "modules/dut_measurement/calibration/kits",
            "modules/dut_measurement/calibration/kits",
            Path(__file__).resolve()
        )
        
        # Ensure directories exist
        os.makedirs(self.osm_results_path, exist_ok=True)
        os.makedirs(self.thru_results_path, exist_ok=True)
        os.makedirs(self.kits_path, exist_ok=True)
        
        # Calibration data storage
        self.measurements = {
            'open': {'freqs': None, 's11': None, 'measured': False},
            'short': {'freqs': None, 's11': None, 'measured': False},
            'match': {'freqs': None, 's11': None, 'measured': False}
        }
        
        self.device_name = None
        self.calibration_date = None
        self.is_complete = False

        # --- Calibration errors ---
        self.e00 = None
        self.e11 = None
        self.delta_e = None

        self.s21m = None  # Measured S21 for THRU
        self.s11m = None  # Measured S11 for THRU

        # --- Calculated errors to return ---
        self.reflection_tracking = None      # Reflection tracking error
        self.transmission_tracking = None    # Transmission tracking error (for Normalization / 1-Port+N)
        self.e22 = None                       # Calculated error for Enhanced-Response
        self.e10e32 = None                    # Another calculated error for Enhanced-Response

        
        logging.info(f"[OSMCalibrationManager] Initialized with base path: {base_path}")
        
    def set_measurement(self, standard_name: str, freqs: np.ndarray, s11: np.ndarray) -> bool:
        """Store measurement for given standard and save as Touchstone file."""
        try:
            standard_name = standard_name.lower()
            if standard_name not in self.measurements:
                logging.error(f"[OSMCalibrationManager] Unknown standard: {standard_name}")
                return False
            
            # Store in memory
            self.measurements[standard_name]['freqs'] = np.array(freqs)
            self.measurements[standard_name]['s11'] = np.array(s11)
            self.measurements[standard_name]['measured'] = True
            
            # Save as Touchstone file
            touchstone_path = os.path.join(self.osm_results_path, f"{standard_name}.s1p")

            self._save_as_touchstone(freqs, s11, touchstone_path, None)
            
            # Check if calibration is complete
            self._check_completion()
            
            logging.info(f"[OSMCalibrationManager] {standard_name.upper()} measurement saved")
            logging.info(f"[OSMCalibrationManager] Touchstone saved: {touchstone_path}")
            
            return True
            
        except Exception as e:
            logging.error(f"[OSMCalibrationManager] Error saving {standard_name}: {e}")
            return False
    
    def _save_as_touchstone(self, freqs: np.ndarray, s11: np.ndarray, filepath: str, filepath_kit: str):
        """Save measurement as Touchstone .s1p file."""
        try:
            # Create scikit-rf Network
            s_data = s11.reshape(-1, 1, 1)  # Reshape for 1-port
            network = rf.Network(frequency=freqs, s=s_data, z0=50)
            
            # Write Touchstone file
            network.write_touchstone(filepath)

            # Save also to KIT path (if provided)
            if filepath_kit:
                network.write_touchstone(filepath_kit)
                logging.info(f"[OSMCalibrationManager] Touchstone file saved (KIT): {filepath_kit}")
            
            logging.info(f"[OSMCalibrationManager] Touchstone file saved: {filepath}")
            
        except Exception as e:
            logging.error(f"[OSMCalibrationManager] Error saving Touchstone file: {e}")
    
    def get_measurement(self, standard_name: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Get measurement data for given standard."""
        standard_name = standard_name.lower()
        if standard_name not in self.measurements:
            return None
        
        data = self.measurements[standard_name]
        if not data['measured']:
            return None
            
        return data['freqs'], data['s11']
    
    def is_standard_measured(self, standard_name: str) -> bool:
        """Check if a standard has been measured."""
        standard_name = standard_name.lower()
        return self.measurements.get(standard_name, {}).get('measured', False)
    
    def is_complete_true(self):
        self.is_complete = True
    
    def _check_completion(self):
        """Check if all standards have been measured."""
        all_measured = all(
            data['measured'] for data in self.measurements.values()
        )
        
        if all_measured and not self.is_complete:
            self.is_complete = True
            self.calibration_date = datetime.now()
            logging.info("[OSMCalibrationManager] OSM calibration is now COMPLETE")
    
    def get_completion_status(self) -> Dict[str, bool]:
        """Return completion status for all standards."""
        return {
            'open': self.measurements['open']['measured'],
            'short': self.measurements['short']['measured'],
            'match': self.measurements['match']['measured'],
            'complete': self.is_complete
        }

    def save_calibration_file(self, filename: str, selected_method: str, is_external_kit: bool, files=None) -> bool:
        """
        Save OSM calibration errors using _save_osm_error_file() instead of storing Open/Short/Match.
        
        Parameters
        ----------
        filename : str
            Name of the calibration file to save.
        selected_method : str
            Calibration method selected (e.g., "OSM (Open - Short - Match)").
        
        Returns
        -------
        bool
            True if save was successful, False otherwise.
        """

        if files is None:
            files = [] 

        try:
            # --- Ensure calibration is complete ---
            if not self.is_complete:
                logging.warning("[OSMCalibrationManager] Cannot save incomplete calibration")
                return False
            
            cal_dir = get_calibration_path(
                "modules/dut_measurement/calibration/osm_results",
                "modules/dut_measurement/calibration/osm_results",
                Path(__file__).resolve()
            )

            self.calibration_dir = cal_dir
            os.makedirs(self.calibration_dir, exist_ok=True)

            kit_subfolder = filename
            kit_path = os.path.join(self.kits_path, kit_subfolder)
            os.makedirs(kit_path, exist_ok=True)
            logging.info(f"[CalibrationManager] Created calibration kit folder: {kit_path}")

            # --- Compute 3-term OSM error model ---

            if not is_external_kit:
                open_file = os.path.join(self.calibration_dir, "open.s1p")
                short_file = os.path.join(self.calibration_dir, "short.s1p")
                match_file = os.path.join(self.calibration_dir, "match.s1p")
            else:
                open_file = files[0] if len(files) > 0 else None
                short_file = files[1] if len(files) > 1 else None
                match_file = files[2] if len(files) > 2 else None

            for f in [open_file, short_file, match_file]:
                if not os.path.exists(f):
                    raise FileNotFoundError(f"[OSMCalibrationManager] Missing calibration file: {f}")

            open_s = rf.Network(open_file)
            short_s = rf.Network(short_file)
            match_s = rf.Network(match_file)

            s_open = open_s.s[:, 0, 0]
            s_short = short_s.s[:, 0, 0]
            s_match = match_s.s[:, 0, 0]
            n_points = len(s_open)

            e00 = np.zeros(n_points, dtype=complex)      # Directivity error
            e11 = np.zeros(n_points, dtype=complex)      # Source match error
            e10e01 = np.zeros(n_points, dtype=complex)   # Reflection tracking error

            logging.info(f"Initialized e00, e11, e10e01 with {n_points} complex zeros.")
            logging.debug(f"e00 sample: {e00[:3]}")

            for i in range(n_points):
                e00[i] = s_match[i]
                e11[i] = (s_open[i] + s_short[i] - 2 * e00[i]) / (s_open[i] - s_short[i])
                e10e01[i] = -2 * (s_open[i] - e00[i]) * (s_short[i] - e00[i]) / (s_open[i] - s_short[i])

            # --- Store errors in self ---
            self.e00 = e00
            self.e11 = e11
            self.e10e01 = e10e01
            self.delta_e = e00 * e11 - e10e01

            # --- Save each error separately using _save_osm_error_file() ---
            freqs = open_s.f
            kit_name = filename
            self._save_osm_error_file(freqs, e00, "directivity.s1p", "Directivity", kit_name)
            self._save_osm_error_file(freqs, e11, "source_match.s1p", "Source match", kit_name)
            self._save_osm_error_file(freqs, e10e01, "reflection_tracking.s1p", "Reflection tracking", kit_name)
            
            logging.info(f"[OSMCalibrationManager] OSM calibration errors saved: {self.error_dir}")
            return True

        except Exception as e:
            logging.error(f"[OSMCalibrationManager] Error saving OSM calibration: {e}")
            return False

    def _save_osm_error_file(self, freq, s_data, filename, label, kit_subfolder=None):
        """
        Save S-parameter data as a Touchstone file inside Kits/<kit_subfolder>.
        Assumes self.kits_path already exists.
        """
        
        save_dir = self.kits_path
        if kit_subfolder:
            save_dir = os.path.join(self.kits_path, kit_subfolder)

        os.makedirs(save_dir, exist_ok=True)
        logging.info(f"[DEBUG] Created folder: {save_dir}")
        print(f"[DEBUG] Created folder: {save_dir}")

        filepath = os.path.join(save_dir, filename)

        network = rf.Network()
        network.frequency = rf.Frequency.from_f(freq, unit="Hz")
        network.s = s_data.reshape((len(freq), 1, 1))
        network.write_touchstone(filepath)

        logging.info(f"[CalibrationErrors] {label} error saved: {filepath}")
        print(f"[DEBUG] Saved {label} in: {filepath}")
    
    def load_calibration_file(self, filename: str) -> bool:
        """Load calibration from .cal file."""
        try:
            if not filename.endswith('.cal'):
                filename += '.cal'
            cal_path = os.path.join(self.kits_path, filename)
            
            if not os.path.exists(cal_path):
                logging.warning(f"[OSMCalibrationManager] Calibration file not found: {cal_path}")
                return False
            
            freqs = []
            short_data = []
            open_data = []
            load_data = []
            
            with open(cal_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 7:
                        freq = float(parts[0])
                        short_r, short_i = float(parts[1]), float(parts[2])
                        open_r, open_i = float(parts[3]), float(parts[4])
                        load_r, load_i = float(parts[5]), float(parts[6])
                        
                        freqs.append(freq)
                        short_data.append(complex(short_r, short_i))
                        open_data.append(complex(open_r, open_i))
                        load_data.append(complex(load_r, load_i))
            
            if freqs:
                # Store loaded data
                freqs = np.array(freqs)
                self.measurements['open']['freqs'] = freqs
                self.measurements['open']['s11'] = np.array(open_data)
                self.measurements['open']['measured'] = True
                
                self.measurements['short']['freqs'] = freqs
                self.measurements['short']['s11'] = np.array(short_data)
                self.measurements['short']['measured'] = True
                
                self.measurements['match']['freqs'] = freqs
                self.measurements['match']['s11'] = np.array(load_data)
                self.measurements['match']['measured'] = True
                
                self._check_completion()
                
                logging.info(f"[OSMCalibrationManager] Calibration loaded from: {cal_path}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OSMCalibrationManager] Error loading calibration file: {e}")
            return False
    
    def list_available_calibrations(self) -> List[str]:
        """List all available .cal files."""
        try:
            cal_files = []
            for file in os.listdir(self.kits_path):
                if file.endswith('.cal'):
                    cal_files.append(file[:-4])  # Remove .cal extension
            return sorted(cal_files)
        except Exception as e:
            logging.error(f"[OSMCalibrationManager] Error listing calibrations: {e}")
            return []
    
    def clear_all_measurements(self):
        """Clear all measurement data."""
        for standard in self.measurements:
            self.measurements[standard] = {'freqs': None, 's11': None, 'measured': False}
        
        self.is_complete = False
        self.calibration_date = None
        logging.info("[OSMCalibrationManager] All measurements cleared")
    
    def apply_calibration(self, freqs: np.ndarray, s11_raw: np.ndarray) -> np.ndarray:
        """
        Apply OSM calibration to raw S11 measurements.
        
        For now this is a placeholder - real OSM correction would use
        error correction formulas involving all three standards.
        """
        if not self.is_complete:
            logging.warning("[OSMCalibrationManager] Cannot apply incomplete calibration")
            return s11_raw
        
        logging.info(f"[OSMCalibrationManager] Applying OSM calibration to {len(s11_raw)} points")
        
        # TODO: Implement actual OSM error correction mathematics
        # This would involve calculating error terms and applying correction
        
        return s11_raw


def get_current_calibration_info(kits_path: str = None) -> Optional[Dict[str, str]]:
    """Get information about currently selected calibration."""
    try:
        if kits_path is None:
            kits_path = os.path.join(os.path.dirname(__file__), "kits")

        # Check for active calibration info
        from PySide6.QtCore import QSettings
        config_file = os.path.join(kits_path, "calibration_config.ini")
        
        if os.path.exists(config_file):
            settings = QSettings(config_file, QSettings.Format.IniFormat)
            
            method = settings.value("Calibration/Method", "---")
            name = settings.value("Calibration/Name", None)
            
            if method and method != "---":
                return {
                    'method': method,
                    'name': name or "Unnamed",
                    'type': 'OSM' if 'OSM' in method else 'Other'
                }
        
        return None
        
    except Exception as e:
        logging.error(f"[get_current_calibration_info] Error: {e}")
        return None


"""
Enhanced THRU calibration manager module for NanoVNA-UTN-Toolkit.
Handles THRU calibrations with persistent state and Touchstone export.
"""
import numpy as np
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import skrf as rf

class THRUCalibrationManager:
    """
    Enhanced THRU calibration manager with persistent state and Touchstone export.
    """

    def __init__(self, base_path: str = None):
   
        base_path = get_calibration_path(
            "modules/dut_measurement/calibration",
            "modules/dut_measurement/calibration",
            Path(__file__).resolve()
        )

        self.base_path = base_path
        self.thru_results_path = os.path.join(base_path, "thru_results")
        self.kits_path = os.path.join(base_path, "kits")

        # Ensure directories exist
        os.makedirs(self.thru_results_path, exist_ok=True)
        os.makedirs(self.kits_path, exist_ok=True)

        # THRU measurement storage
        self.measurements = {
            'thru': {'freqs': None, 's21': None, 'measured': False}
        }

        self.device_name = None
        self.calibration_date = None
        self.is_complete = False

        logging.info(f"[THRUCalibrationManager] Initialized with base path: {base_path}")

    # ------------------- Measurement Handling -------------------
    def set_measurement(self, standard_name: str, freqs: np.ndarray, s11: np.ndarray, s21: np.ndarray) -> bool:
        """Store THRU measurement and save as Touchstone file."""
        
        freqs = np.asarray(freqs, dtype=np.float64)
        s21 = np.asarray(s21, dtype=np.complex128)

        self.s11m = s11
        self.s21m = s21

        logging.info(f"S21 dtype before copy: {s21.dtype}")
        logging.info(f"S21 shape before copy: {s21.shape}")
        logging.info(f"S21 first raw: {s21[:5]}")

        try:
            self.measurements[standard_name]['freqs'] = np.array(freqs)
            self.measurements[standard_name]['s11'] = np.array(s11)
            self.measurements[standard_name]['s21'] = np.array(s21)
            self.measurements[standard_name]['measured'] = True
            self.is_complete = True
            self.calibration_date = datetime.now()

            touchstone_path = os.path.join(self.thru_results_path, "thru.s2p")
            self._save_as_touchstone(freqs, s11, s21, touchstone_path)

            logging.info(f"[THRUCalibrationManager] THRU measurement saved")
            logging.info(f"[THRUCalibrationManager] Touchstone saved: {touchstone_path}")
            return True
        except Exception as e:
            logging.error(f"[THRUCalibrationManager] Error saving THRU measurement: {e}")
            return False

    def _save_as_touchstone(self, freqs, s11, s21, filepath):
        try:
            s_data = np.zeros((len(freqs), 2, 2), dtype=complex)

            s_data[:, 0, 0] = s11
            s_data[:, 1, 0] = s21

            network = rf.Network()
            network.frequency = rf.Frequency.from_f(freqs, unit="Hz")
            network.s = s_data
            network.z0 = 50

            filepath = os.path.splitext(filepath)[0]

            network.write_touchstone(filepath)

            logging.info(f"[THRUCalibrationManager] Touchstone S2P file saved: {filepath}.s2p")

        except Exception as e:
            logging.error(f"[THRUCalibrationManager] Error writing Touchstone S2P file: {e}")
            
    def get_measurement(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return THRU measurement data if available."""
        data = self.measurements['thru']
        if not data['measured']:
            return None
        return data['freqs'], data['s21']

    def is_standard_measured(self, standard_name: str = 'thru') -> bool:
        """Check if THRU has been measured."""
        return self.measurements.get('thru', {}).get('measured', False)

    def is_complete_true(self):
        self.is_complete = True

    def _check_completion(self):
        """Check if THRU calibration is complete."""
        if self.measurements['thru']['measured'] and not self.is_complete:
            self.is_complete = True
            self.calibration_date = datetime.now()
            logging.info("[THRUCalibrationManager] THRU calibration is now COMPLETE")

    def get_completion_status(self) -> Dict[str, bool]:
        """Return completion status like OSM interface expects."""
        return {'thru': self.measurements['thru']['measured'], 'complete': self.is_complete}

    def read_thru_file(self, thru_file_path):

        network = rf.Network(thru_file_path)
        freqs = network.frequency.f  # Freqs
        s11 = network.s[:, 0, 0]    # S11
        s21 = network.s[:, 1, 0]    # S21
        return s11, s21, freqs

    def save_calibration_file(self, filename: str, selected_method: str, is_external_kit: bool, files=None, osm_instance=None):
        """
        Save calibration file and compute errors depending on the selected method.

        Returns
        -------
        dict
            Calculated errors:
            - 'reflection_tracking': always returned (based on s11)
            - 'transmission_tracking': returned for Normalization / 1-Port+N
            - 'e22', 'e10e32': returned for Enhanced-Response
        """

        if files is None:
            files = []

        try:
            if not self.is_complete:
                logging.warning("[CalibrationManager] Cannot save incomplete calibration")
                return False, {}

            # --- Create kit subfolder ---
            kit_subfolder = filename
            kit_path = os.path.join(self.kits_path, kit_subfolder)
            os.makedirs(kit_path, exist_ok=True)
            logging.info(f"[CalibrationManager] Created calibration kit folder: {kit_path}")

            errors = {}

            if not is_external_kit:

                logging.info(f"[CalibrationManager] Selected method: {selected_method}")

                if selected_method == "Normalization":
                    s21 = self.measurements['thru']['s21']
                    freqs = self.measurements['thru']['freqs']
                    errors['transmission_tracking'] = s21

                    s = np.zeros((len(freqs), 2, 2), dtype=complex)
                    s[:, 1, 0] = s21

                elif selected_method == "1-Port+N":
                    s21 = self.measurements['thru']['s21']
                    freqs = self.measurements['thru']['freqs']
                    errors['transmission_tracking'] = s21

                    s = np.zeros((len(freqs), 2, 2), dtype=complex)
                    s[:, 1, 0] = s21

                elif selected_method == "Enhanced-Response":
                    s11m = self.measurements['thru']['s11']
                    s21m = self.measurements['thru']['s21']
                    freqs = self.measurements['thru']['freqs']
                    e00 = osm_instance.e00
                    e11 = osm_instance.e11
                    delta_e = osm_instance.delta_e

                    missing = []
                    if s11m is None:
                        missing.append("s11m")
                    if s21m is None:
                        missing.append("s21m")
                    if e00 is None:
                        missing.append("e00")
                    if e11 is None:
                        missing.append("e11")
                    if delta_e is None:
                        missing.append("delta_e")

                    if missing:
                        logging.error(f"[THRUCalibrationManager] Cannot compute Enhanced-Response: missing {', '.join(missing)}")
                        return False, {}
            else:
                if selected_method == "Normalization":
                    s11, s21, freqs = self.read_thru_file(files[3])
                    errors['transmission_tracking'] = s21

                    s = np.zeros((len(freqs), 2, 2), dtype=complex)
                    s[:, 1, 0] = s21

                elif selected_method == "1-Port+N":
                    s11, s21, freqs = self.read_thru_file(files[3])
                    errors['transmission_tracking'] = s21

                    s = np.zeros((len(freqs), 2, 2), dtype=complex)
                    s[:, 1, 0] = s21

                elif selected_method == "Enhanced-Response":
                    s11m, s21m, freqs = self.read_thru_file(files[3])
                    e00 = osm_instance.e00
                    e11 = osm_instance.e11
                    delta_e = osm_instance.delta_e
                    
                    missing = []
                    if s11m is None:
                        missing.append("s11m")
                    if s21m is None:
                        missing.append("s21m")
                    if e00 is None:
                        missing.append("e00")
                    if e11 is None:
                        missing.append("e11")
                    if delta_e is None:
                        missing.append("delta_e")

                    if missing:
                        logging.error(f"[THRUCalibrationManager] Cannot compute Enhanced-Response: missing {', '.join(missing)}")
                        return False, {}

            # === NORMALIZATION ===
            if selected_method == "Normalization":

                self._save_thru_error_file(freqs, s, "transmission_tracking.s2p", "Transmission tracking", kit_subfolder)

            # === 1-PORT+N ===
            elif selected_method == "1-Port+N":
              
                self._save_thru_error_file(freqs, s, "transmission_tracking.s2p", "Transmission tracking", kit_subfolder)

            # === ENHANCED-RESPONSE ===
            elif selected_method == "Enhanced-Response":

                # e22 = (S11M - e00) / (S11M * e11 - delta_e)
                e22 = (s11m - e00) / (s11m * e11 - delta_e)
                # e10e32 = S21M * (1 - e11 * e22)
                e10e32 = s21m * (1 - (e11 * e22))

                e22_save = np.zeros((len(freqs), 2, 2), dtype=complex)
                e22_save[:, 1, 0] = e22

                e10e32_save = np.zeros((len(freqs), 2, 2), dtype=complex)
                e10e32_save[:, 1, 0] = e10e32

                logging.info(f"[CalibrationManager] Calculated e22 and e10e32 for Enhanced-Response: e22={e22}, e10e32={e10e32}")

                self._save_thru_error_file(freqs, e22_save, "load_match.s2p", "Load Match", kit_subfolder)
                self._save_thru_error_file(freqs, e10e32_save, "transmission_tracking.s2p", "Transmission tracking", kit_subfolder)

            logging.info(f"[CalibrationManager] Calibration kit saved in: {kit_path}")
            return True, errors

        except Exception as e:
            logging.error(f"[CalibrationManager] Error saving calibration file: {e}")
            return False, {}

    def _save_thru_error_file(self, freq, s_data, filename, label, kit_subfolder=None):
        """
        Save S-parameter data as a Touchstone file inside Kits/<kit_subfolder>.
        Assumes self.kits_path already exists.
        """
        save_dir = self.kits_path
        if kit_subfolder:
            save_dir = os.path.join(self.kits_path, kit_subfolder)

        os.makedirs(save_dir, exist_ok=True)
        logging.info(f"[DEBUG] Created folder_thru data: {s_data}")
        logging.info(f"[DEBUG] Created folder_thru: {save_dir}")

        filepath = os.path.join(save_dir, filename)

        network = rf.Network()
        network.frequency = rf.Frequency.from_f(freq, unit="Hz")
        network.s = s_data.reshape((len(freq), 2, 2))
        network.write_touchstone(filepath)

        logging.info(f"[CalibrationErrors] {label} error saved: {filepath}")
        print(f"[DEBUG] Saved {label} in: {filepath}")

    def load_calibration_file(self, filename: str) -> bool:
        """Load THRU calibration data from .cal file."""
        try:
            if not filename.endswith('.cal'):
                filename += '.cal'
            cal_path = os.path.join(self.kits_path, filename)

            if not os.path.exists(cal_path):
                logging.warning(f"[THRUCalibrationManager] File not found: {cal_path}")
                return False

            freqs = []
            s21_data = []

            with open(cal_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        freqs.append(float(parts[0]))
                        s21_data.append(complex(float(parts[1]), float(parts[2])))

            if freqs:
                self.measurements['thru']['freqs'] = np.array(freqs)
                self.measurements['thru']['s21'] = np.array(s21_data)
                self.measurements['thru']['measured'] = True
                self.is_complete = True
                self.calibration_date = datetime.now()
                logging.info(f"[THRUCalibrationManager] Calibration loaded from: {cal_path}")
                return True

            return False
        except Exception as e:
            logging.error(f"[THRUCalibrationManager] Error loading calibration file: {e}")
            return False

    def list_available_calibrations(self) -> List[str]:
        """List all available .cal files for THRU calibration."""
        try:
            cal_files = []
            for file in os.listdir(self.kits_path):
                if file.endswith('.cal'):
                    cal_files.append(file[:-4])
            return sorted(cal_files)
        except Exception as e:
            logging.error(f"[THRUCalibrationManager] Error listing calibrations: {e}")
            return []

    def clear_all_measurements(self):
        """Clear all measurement data."""
        self.measurements['thru'] = {'freqs': None, 's21': None, 'measured': False}
        self.is_complete = False
        self.calibration_date = None
        logging.info("[THRUCalibrationManager] All measurements cleared")

    def apply_calibration(self, freqs: np.ndarray, s21_raw: np.ndarray) -> np.ndarray:
        """
        Apply THRU normalization to raw S21 data.
        Placeholder - real THRU correction may involve dividing by measured THRU.
        """
        if not self.is_complete:
            logging.warning("[THRUCalibrationManager] Cannot apply incomplete calibration")
            return s21_raw

        cal_freqs = self.measurements['thru']['freqs']
        cal_s21 = self.measurements['thru']['s21']

        if not np.array_equal(freqs, cal_freqs):
            cal_s21_interp = np.interp(freqs, cal_freqs, cal_s21)
        else:
            cal_s21_interp = cal_s21

        s21_corrected = s21_raw / cal_s21_interp
        logging.info("[THRUCalibrationManager] THRU calibration applied successfully")
        return s21_corrected
