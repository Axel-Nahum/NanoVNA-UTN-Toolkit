"""
Custom logging handler for GUI applications.
"""
import logging
from PySide6.QtCore import QTimer


class GuiLogHandler(logging.Handler):
    """Custom logging handler that forwards log messages to the GUI."""
    
    def __init__(self, gui_app):
        super().__init__()
        self.gui_app = gui_app
    
    def emit(self, record):
        """Process and emit log records to the GUI."""
        try:
            if record.name.startswith('NanoVNA_UTN_Toolkit.Hardware.VNA'):
                message = self.format(record)
                
                # Handle different types of hardware logs
                if 'exec_command(' in message:
                    cmd = message.split('exec_command(')[1].split(')')[0]
                    # Use QTimer to ensure thread safety
                    QTimer.singleShot(0, lambda: self.gui_app.log_message(f"Executing command: {cmd}"))
                    
                elif 'result:' in message and 'Commands:' in message:
                    # Extract available commands from VNA
                    result_part = message.split('result:')[1].strip()
                    if result_part.startswith('[') and 'Commands:' in result_part:
                        try:
                            import ast
                            commands_list = ast.literal_eval(result_part)
                            if commands_list and len(commands_list) > 1:
                                commands = ', '.join(commands_list[1:8])  # Show first 7 commands
                                if len(commands_list) > 8:
                                    commands += f'... (+{len(commands_list)-8} more)'
                                QTimer.singleShot(0, lambda c=commands: self.gui_app.log_message(f"Available commands: {c}"))
                        except:
                            pass  # If parsing fails, ignore
                            
                elif 'Firmware Version:' in message:
                    version_part = message.split('Firmware Version:')[1].strip().replace("['", "").replace("']", "")
                    QTimer.singleShot(0, lambda v=version_part: self.gui_app.log_message(f"Firmware version detected: {v}"))
                    
                elif 'Found NanoVNA USB:' in message:
                    # Extract port info
                    parts = message.split('Found NanoVNA USB:')
                    if len(parts) > 1:
                        port_info = parts[1].strip()
                        QTimer.singleShot(0, lambda p=port_info: self.gui_app.log_message(f"Found: NanoVNA USB: {p}"))
                        
                elif 'VNA done reading frequencies' in message:
                    freq_part = message.split('VNA done reading frequencies (')[1].split(' values)')[0]
                    QTimer.singleShot(0, lambda f=freq_part: self.gui_app.log_message(f"Read {f} frequencies from device"))
                    
        except Exception:
            pass  # Ignore handler errors to prevent infinite loops
