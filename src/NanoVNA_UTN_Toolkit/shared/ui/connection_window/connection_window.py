"""
Connection status window for NanoVNA devices.
"""
from NanoVNA_UTN_Toolkit.utils import safe_import
import os
import sys
import logging
from ....workers.device_worker import DeviceWorker
from ....modules.dut_measurement.ui.log_handler import GuiLogHandler

from pathlib import Path

from PySide6.QtCore import QTimer, QThread, Qt, QSettings
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton,
    QHBoxLayout, QProgressBar, QFrame, QGridLayout, QGroupBox, QLabel, QScrollArea
)
from PySide6.QtGui import QIcon, QFont, QGuiApplication

ModuleSelectionWindow = safe_import("NanoVNA_UTN_Toolkit.modules.menu_window", "ModuleSelectionWindow")
    
get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

dark_light_config = safe_import("NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config")

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")

JsonResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.json_resource_loader", "JsonResourceLoader")

# ----------------------------------------------------------------------------------------------------------------------------- #

class NanoVNAStatusApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini", 
            "shared/utils/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        )

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON 
# ------------------------------------------------------------------------------------------------------------------- #

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini", 
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_connection.json"
        )

        self.resourceLoader.load_connection_resources()

# ------------------------------------------------------------------------------------------------------------------- #
# Dark light Mode
# ------------------------------------------------------------------------------------------------------------------- #

        # Dark-Light mode settings

        dark_light_config(self)

# ------------------------------------------------------------------------------------------------------------------- #

        # Qframe
        qframe_color = settings.value("Dark_Light/Qframe/background-color", "white")

        self.vna = None
        self.is_checking = False
        self.worker = None
        self.worker_thread = None
        
        self.init_ui(qframe_color=qframe_color)
        self.setup_hardware_logging()
        
        # Start initial device check
        QTimer.singleShot(1000, self.start_device_check)
        
        # Log initial message
        self.log_message("Application started. Preparing device detection...")
    
    def init_ui(self, qframe_color):
        """Initialize the user interface."""
        # Try to set application icon

        apply_window_icon(self)

        self.setWindowTitle(f"{self.device_info_title}")
        self.setGeometry(100, 100, 900, 700)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()

        center_point = screen.center()
        window_geometry.moveCenter(center_point)

        self.move(window_geometry.topLeft())

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Status section
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_frame.setFrameStyle(QFrame.Shape.Box)

        status_frame.setStyleSheet(f"""
            QFrame#statusFrame {{
                border: 1px solid {qframe_color};
            }}
        """)

        status_layout = QVBoxLayout(status_frame)
        
        # Connection status label
        self.status_label = QLabel(f"{self.connection_status_starting}")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: orange; padding: 10px;")
        status_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        status_layout.addWidget(self.progress_bar)
        
        # Current operation label
        self.operation_label = QLabel("Preparing system...")
        self.operation_label.setStyleSheet("font-size: 12px; padding: 5px;")
        status_layout.addWidget(self.operation_label)
        
        layout.addWidget(status_frame)

        # Load configuration for UI colors and styles

        settings = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        ) 

        groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
        color = groupbox_border.split()[-1]
        groupbox_style = f"QGroupBox {{ border: 2px solid {color}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; font-size: 30pt;}}"
        
        # Device information section
        self.device_group = QGroupBox(f"{self.device_info_title}")
        self.device_group.setStyleSheet(groupbox_style)
        
        device_layout = QGridLayout(self.device_group)
        
        # Create labels for device information
        self.board_label = QLabel(f"{self.device_info_board_label}")
        self.board_value = QLabel(f"{self.device_info_board_value}")
        self.version_label = QLabel(f"{self.device_info_version_label}")
        self.version_value = QLabel(f"{self.device_info_version_value}")
        self.build_time_label = QLabel(f"{self.device_info_built_time_label}")
        self.build_time_value = QLabel(f"{self.device_info_built_time_value}")
        self.arch_label = QLabel(f"{self.device_info_architecture_label}")
        self.arch_value = QLabel(f"{self.device_info_architecture_value}")
        self.platform_label = QLabel(f"{self.device_info_platform_label}")
        self.platform_value = QLabel(f"{self.device_info_platform_value}")
        
        # Extended device information
        self.serial_label = QLabel(f"{self.device_info_serial_label}")
        self.serial_value = QLabel(f"{self.device_info_serial_value}")
        self.device_type_label = QLabel(f"{self.device_info_type_label}")
        self.device_type_value = QLabel(f"{self.device_info_type_value}")
        
        # Parameters section
        self.params_label = QLabel(f"{self.device_info_parameters_label}")
        self.params_value = QLabel(f"{self.device_info_parameters_value}")
        
        # Features section
        self.features_label = QLabel(f"{self.device_info_features_label}")
        
        # Create scrollable features area
        self.features_scroll_area = QScrollArea()
        self.features_scroll_area.setWidgetResizable(True)
        self.features_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.features_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.features_scroll_area.setMinimumHeight(80)
        self.features_scroll_area.setMaximumHeight(150)  # Limit max height
        
        # Create features content widget
        self.features_content = QLabel(f"{self.device_info_features_value}")
        self.features_content.setWordWrap(True)
        self.features_content.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.features_content.setStyleSheet("padding: 5px; background-color: transparent; color: palette(text);")
        
        # Set the content widget for the scroll area
        self.features_scroll_area.setWidget(self.features_content)
        
        # Style the labels
        label_style = "font-weight: bold;"
        value_style = "padding-left: 10px;"
        
        for label in [self.board_label, self.version_label, self.build_time_label, 
                     self.arch_label, self.platform_label, self.serial_label, 
                     self.device_type_label, self.params_label, self.features_label]:
            label.setStyleSheet(label_style)
        
        for value in [self.board_value, self.version_value, self.build_time_value,
                     self.arch_value, self.platform_value, self.serial_value,
                     self.device_type_value, self.params_value]:
            value.setStyleSheet(value_style)
        
        # Style features scroll area
        self.features_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid palette(mid);
                border-radius: 5px;
                background-color: palette(base);
            }
            QScrollBar:vertical {
                background: palette(button);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: palette(mid);
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: palette(dark);
            }
        """)
        
        # Add to grid layout
        device_layout.addWidget(self.board_label, 0, 0)
        device_layout.addWidget(self.board_value, 0, 1)
        device_layout.addWidget(self.version_label, 1, 0)
        device_layout.addWidget(self.version_value, 1, 1)
        device_layout.addWidget(self.device_type_label, 2, 0)
        device_layout.addWidget(self.device_type_value, 2, 1)
        device_layout.addWidget(self.serial_label, 3, 0)
        device_layout.addWidget(self.serial_value, 3, 1)
        device_layout.addWidget(self.platform_label, 4, 0)
        device_layout.addWidget(self.platform_value, 4, 1)
        device_layout.addWidget(self.arch_label, 5, 0)
        device_layout.addWidget(self.arch_value, 5, 1)
        device_layout.addWidget(self.build_time_label, 6, 0)
        device_layout.addWidget(self.build_time_value, 6, 1)
        device_layout.addWidget(self.params_label, 7, 0)
        device_layout.addWidget(self.params_value, 7, 1)
        device_layout.addWidget(self.features_label, 8, 0)
        device_layout.addWidget(self.features_scroll_area, 8, 1)
        
        layout.addWidget(self.device_group)
        
        # Console output section
        console_label = QLabel("LOGS:")
        console_label.setStyleSheet("font-weight: bold; margin-top: 10px; font-size: 14px;")
        layout.addWidget(console_label)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Courier", 9))
        self.console.setMaximumHeight(200)
        self.console.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {qframe_color};
            }}
        """)
        layout.addWidget(self.console)
        
        # Buttons section
        button_layout = QHBoxLayout()
        
        # Layout horizontal para los primeros botones
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton(f"{self.refresh_button_label}")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        button_layout.addWidget(self.refresh_btn)

        self.disconnect_btn = QPushButton(f"{self.disconnect_button_label}")
        self.disconnect_btn.clicked.connect(self.manual_disconnect)
        self.disconnect_btn.setEnabled(False)  # Initially disabled
        self.disconnect_btn.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        button_layout.addWidget(self.disconnect_btn)

        clear_btn = QPushButton(f"{self.clear_log_button_label}")
        clear_btn.clicked.connect(self.console.clear)
        clear_btn.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        button_layout.addWidget(clear_btn)

        self.stop_btn = QPushButton(f"{self.stop_button_label}")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        button_layout.addWidget(self.stop_btn)

        layout.addLayout(button_layout)

        self.smith_btn = QPushButton(f"{self.open_menu_button_label}")
        self.smith_btn.clicked.connect(self.open_selection_window)
        self.stop_btn.setEnabled(False)
        self.smith_btn.setStyleSheet("padding: 12px; font-size: 14px;")
        layout.addWidget(self.smith_btn)

        # Show window
        self.show()
    
    def setup_hardware_logging(self):
        """Setup custom logging handler to capture important hardware logs."""
        handler = GuiLogHandler(self)
        handler.setLevel(logging.DEBUG)
        
        # Add handler to VNA logger
        vna_logger = logging.getLogger('NanoVNA_UTN_Toolkit.Hardware.VNA')
        vna_logger.addHandler(handler)
    
    def update_progress(self, value):
        """Update progress bar."""
        self.progress_bar.setValue(value)
    
    def update_operation_status(self, status):
        """Update operation status label."""
        self.operation_label.setText(status)
    
    def update_device_info(self, device_info, vna=None):
        """Update device information display."""
        self.board_value.setText(device_info.get('board', 'Unknown'))
        self.version_value.setText(device_info.get('version', 'Unknown'))
        self.build_time_value.setText(device_info.get('build_time', 'Unknown'))
        self.arch_value.setText(device_info.get('architecture', 'Unknown'))
        self.platform_value.setText(device_info.get('platform', 'Unknown'))
        
        # Extended device information
        self.serial_value.setText(device_info.get('serial_number', 'Not available'))
        self.device_type_value.setText(type(vna).__name__ if vna else device_info.get('device_type', 'Unknown'))
        
        # Handle parameters
        params = device_info.get('parameters', {})
        if params:
            param_labels = {
                'p': 'Points',
                'IF': 'IF Frequency',
                'ADC': 'ADC Rate',
                'Lcd': 'LCD Resolution'
            }
            
            param_text = ""
            for key, value in params.items():
                label = param_labels.get(key, key)
                param_text += f"• {label}: {value}\n"
            self.params_value.setText(param_text.strip())
        else:
            self.params_value.setText("Not available")
        
        # Handle features - enhanced with VNA device capabilities
        features = device_info.get('features', [])
        
        # Add device-specific capabilities if VNA object available
        if vna:
            # Add valid datapoints information
            if hasattr(vna, 'valid_datapoints') and vna.valid_datapoints:
                datapoints_str = ', '.join(map(str, vna.valid_datapoints))
                features.append(f"Valid data points: {datapoints_str}")
            
            # Add sweep range information  
            if hasattr(vna, 'sweep_points_min') and hasattr(vna, 'sweep_points_max'):
                features.append(f"Sweep range: {vna.sweep_points_min} - {vna.sweep_points_max}")
            
            # Add frequency range if available
            if hasattr(vna, 'sweep_max_freq_hz'):
                max_freq_ghz = vna.sweep_max_freq_hz / 1e9
                features.append(f"Max frequency: {max_freq_ghz:.1f} GHz")
            
            # Get device features if method exists
            if hasattr(vna, 'get_features') and callable(getattr(vna, 'get_features')):
                try:
                    device_features = vna.get_features()
                    if device_features:
                        features.extend(device_features)
                except Exception as e:
                    logging.debug(f"Could not get device features: {e}")
        
        if features:
            # Show all relevant features (no more truncation - scrollable area will handle overflow)
            important_features = []
            for feature in features:
                if any(keyword in feature.lower() for keyword in ['customizable', 'screenshot', 'sn', 'bandwidth', 'average', 'power', 'data points', 'sweep', 'frequency']):
                    important_features.append(feature)
            
            # Also include any other features that might be relevant
            for feature in features:
                if feature not in important_features:
                    important_features.append(feature)
            
            if important_features:
                features_text = "• " + "\n• ".join(important_features)  # Show ALL features
                self.features_content.setText(features_text)
            else:
                self.features_content.setText(f"{len(features)} features available")
        else:
            self.features_content.setText("Not available")
    
    def clear_device_info(self):
        """Clear the device information display."""
        self.board_value.setText("Not detected")
        self.version_value.setText("Unknown")
        self.build_time_value.setText("Unknown")
        self.arch_value.setText("Unknown")
        self.platform_value.setText("Unknown")
        self.serial_value.setText("Not available")
        self.device_type_value.setText("Unknown")
        self.params_value.setText("Not available")
        self.features_content.setText("Not available")
    
    def log_message(self, message):
        """Add a message to the console output."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.console.append(formatted_message)
        # Move cursor to end
        cursor = self.console.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.console.setTextCursor(cursor)
        logging.getLogger(__name__).info(message)
    
    def start_device_check(self):
        """Start device detection in a separate thread."""
        if self.is_checking:
            self.log_message("Device search is already running")
            return
            
        self.is_checking = True
        self.refresh_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Clear previous device info
        self.clear_device_info()
        
        # Clean up previous thread if exists (non-blocking)
        if self.worker_thread and self.worker_thread.isRunning():
            self.log_message("Stopping previous search...")
            if self.worker:
                self.worker.stop()
            # Use non-blocking cleanup with signal connection
            self.worker_thread.finished.connect(self._start_new_detection)
            self.worker_thread.quit()
            return  # Exit here, _start_new_detection will be called when thread finishes
        
        # Start new detection immediately if no previous thread
        self._start_new_detection()
    
    def _start_new_detection(self):
        """Internal method to start new detection after cleanup."""
        # Disconnect the signal to prevent multiple connections
        if self.worker_thread:
            try:
                self.worker_thread.finished.disconnect(self._start_new_detection)
            except RuntimeError:
                pass  # Signal was not connected, ignore error
        
        # Create worker thread
        self.worker_thread = QThread()
        self.worker = DeviceWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.status_update.connect(self.update_operation_status)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.device_found.connect(self.on_device_found)
        self.worker.device_error.connect(self.on_device_error)
        self.worker.finished.connect(self.on_detection_finished)
        
        # Connect thread signals
        self.worker_thread.started.connect(self.worker.detect_devices)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        # Start the thread
        self.worker_thread.start()
        self.log_message("Starting device search in background...")
    
    def stop_detection(self):
        """Stop the current detection process."""
        if self.worker:
            self.worker.stop()
            self.log_message("Stopping device search...")

    def open_selection_window(self):
        """Open the welcome window."""
        # Log device transfer to welcome window
        if self.vna:
            device_type = type(self.vna).__name__
            self.log_message(f"[connection_window.open_selection_window] Device {device_type} available - passing to welcome window")
            self.selection_windows = ModuleSelectionWindow(vna_device=self.vna)
        else:
            self.log_message("[connection_window.open_selection_window] No device connected - using placeholder mode")
            self.selection_windows = ModuleSelectionWindow()
            
        self.selection_windows.show()
        self.close() 

    def manual_refresh(self):
        """Manual refresh button handler."""
        self.log_message("Manual refresh requested")
        self.start_device_check()
    
    def manual_disconnect(self):
        """Manual disconnect button handler."""
        if self.vna:
            try:
                if hasattr(self.vna, 'disconnect'):
                    self.vna.disconnect()
                self.log_message("Device disconnected manually")
            except Exception as e:
                self.log_message(f"Error disconnecting: {str(e)}")
            finally:
                self.vna = None
                self.status_label.setText(f"{self.connection_status_disconnected}")
                self.status_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold; padding: 10px;")
                self.clear_device_info()
                self.disconnect_btn.setEnabled(False)
    
    def on_device_found(self, vna, device_info):
        """Handle successful device detection."""
        self.vna = vna
        self.status_label.setText(f"{self.connection_status_connected}")
        self.status_label.setStyleSheet("color: green; font-size: 16px; font-weight: bold; padding: 10px;")
        
        # Update device information display - pass VNA object for enhanced info
        self.update_device_info(device_info, vna)
        
        # Enable disconnect button
        self.disconnect_btn.setEnabled(True)
        
        # Enhanced logging for device detection
        board = device_info.get('board', 'Unknown')
        version = device_info.get('version', 'Unknown')
        device_type = type(vna).__name__ if vna else 'Unknown'
        
        self.log_message(f"[connection_window.on_device_found] Device connected: {board} (Type: {device_type})")
        self.log_message(f"Device Details - Version: {version}")
        
        # Log device capabilities if available
        if hasattr(vna, 'sweep_points_min') and hasattr(vna, 'sweep_points_max'):
            self.log_message(f"Sweep Points Range: {vna.sweep_points_min} - {vna.sweep_points_max}")
        
        # Log device attributes for debugging
        self.log_message(f"Device Object: {device_type}")
        self.log_message(f"Device Attributes: {[attr for attr in dir(vna) if not attr.startswith('_')][:10]}...")
        
        self.log_message("Connection successful - Automatic search paused")
        
        # Log full device info if available
        if device_info.get('full_text'):
            self.log_message("Complete device information:")
            for line in device_info['full_text'].split('\n'):
                if line.strip():
                    self.log_message(f"   {line.strip()}")
    
    def on_device_error(self, error_msg):
        """Handle device detection errors."""
        self.status_label.setText("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold; padding: 10px;")
        self.clear_device_info()
        self.log_message(f"{error_msg}")
        
        # Disable disconnect button
        self.disconnect_btn.setEnabled(False)
        
        # Clean up VNA connection
        if self.vna:
            try:
                if hasattr(self.vna, 'disconnect'):
                    self.vna.disconnect()
            except:
                pass
            self.vna = None  # Clear the VNA reference so periodic checks can resume
    
    def on_detection_finished(self):
        """Handle detection process completion."""
        self.is_checking = False
        self.refresh_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Clean up thread properly
        if self.worker_thread:
            # Ensure thread completes and is cleaned up
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(2000)  # Wait up to 2 seconds
            self.worker_thread = None
        
        # Clear worker reference
        if self.worker:
            self.worker = None
    
    def closeEvent(self, event):
        """Handle application close event."""
        logger = logging.getLogger(__name__)
        logger.info("Application closing - cleaning up resources...")
        
        # Stop worker if running
        if self.worker:
            logger.debug("Stopping worker...")
            self.worker.stop()
        
        # Clean up VNA connection
        if self.vna:
            logger.debug("Disconnecting VNA...")
            try:
                if hasattr(self.vna, 'disconnect'):
                    self.vna.disconnect()
                elif hasattr(self.vna, 'close'):
                    self.vna.close()
            except Exception as e:
                logger.debug(f"Error disconnecting VNA: {e}")
        
        # Wait for thread to finish properly
        if self.worker_thread and self.worker_thread.isRunning():
            logger.debug("Waiting for worker thread to finish...")
            self.worker_thread.quit()
            if not self.worker_thread.wait(5000):  # Wait up to 5 seconds
                logger.warning("Thread did not finish gracefully, forcing termination")
                self.worker_thread.terminate()
                self.worker_thread.wait(1000)  # Wait 1 more second after terminate
        
        logger.info("Application cleanup completed")
        event.accept()
