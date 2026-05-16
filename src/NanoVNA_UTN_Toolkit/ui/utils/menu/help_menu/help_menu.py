import webbrowser

import os
import sys

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QMessageBox, QDialog, QTextEdit
)

# Import get_settings 

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

class AboutDialog(QDialog):
    """
    About dialog that displays the project README.md file in a scrollable window.
    Supports both English and Spanish versions.
    """
    
    def __init__(self, parent=None, language='en'):
        """
        Initialize the About dialog.
        
        Args:
            parent: Parent widget
            language: Language code ('en' for English, 'es' for Spanish)
        """
        super().__init__(parent)
        self.language = language
        
        if language == 'es':
            self.setWindowTitle("NanoVNA UTN Toolkit - Acerca de NanoVNA UTN Toolkit")
        else:
            self.setWindowTitle("NanoVNA UTN Toolkit - About NanoVNA UTN Toolkit")

        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_readme()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create a text widget with scroll capability
        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)
        
        # Configure scrolling: vertical only, no horizontal scroll
        self.text_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Enable word wrap to fit content to window width
        self.text_widget.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Apply comprehensive CSS to force ALL code elements to wrap
        css_style = """
        QTextEdit {
            font-family: system-ui, -apple-system, sans-serif;
            line-height: 1.4;
        }
        pre, code, .codehilite, .highlight {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
            word-break: break-all !important;
            max-width: 100% !important;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
            background-color: #f5f5f5 !important;
            padding: 8px !important;
            border-radius: 4px !important;
            border: 1px solid #e0e0e0 !important;
            overflow-x: hidden !important;
        }
        pre code {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
            word-break: break-all !important;
        }
        """
        self.text_widget.setStyleSheet(css_style)
        
        # Enable markdown rendering
        self.text_widget.setMarkdown("")
        
        layout.addWidget(self.text_widget)
    
    def _load_readme(self):
        """Load and display the appropriate README file based on language."""
        
        try:
            # Get the project root directory (go up from ui/graphics_window.py to project root)
            if hasattr(sys, '_MEIPASS'):
                project_root = sys._MEIPASS
            else:
                project_root = Path(__file__).resolve().parents[6]
            
            if self.language == 'es':
                readme_path = os.path.join(project_root, "README_ES.md")
                fallback_text = (
                    "Archivo README_ES.md no encontrado.\n\n"
                    f"Ubicación esperada: {readme_path}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "Un toolkit integral para mediciones y análisis con NanoVNA."
                )
            else:
                readme_path = os.path.join(project_root, "README.md")
                fallback_text = (
                    "README.md file not found.\n\n"
                    f"Expected location: {readme_path}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "A comprehensive toolkit for NanoVNA measurements and analysis."
                )
            
            if os.path.exists(readme_path):
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                
                # Process content to ensure code blocks wrap properly
                processed_content = self._process_content_for_wrapping(readme_content)
                self.text_widget.setMarkdown(processed_content)
            else:
                self.text_widget.setPlainText(fallback_text)
                
        except Exception as e:
            if self.language == 'es':
                error_text = (
                    f"Error cargando README_ES.md: {str(e)}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "Un toolkit integral para mediciones y análisis con NanoVNA."
                )
            else:
                error_text = (
                    f"Error loading README.md: {str(e)}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "A comprehensive toolkit for NanoVNA measurements and analysis."
                )
            self.text_widget.setPlainText(error_text)

    def _process_content_for_wrapping(self, content):
        """Process markdown content to ensure code blocks wrap properly."""
        import re
        
        # Find all code blocks (both ``` and indented)
        # Pattern for fenced code blocks
        fenced_pattern = r'```(\w*)\n(.*?)\n```'
        
        def replace_fenced_code(match):
            lang = match.group(1)
            code = match.group(2)
            # Break long lines in code blocks
            lines = code.split('\n')
            processed_lines = []
            for line in lines:
                if len(line) > 80:  # Break lines longer than 80 characters
                    # For command lines, try to break at logical points
                    if line.strip().startswith('python') and '--' in line:
                        # Break at command line arguments
                        parts = line.split(' --')
                        if len(parts) > 1:
                            reconstructed = parts[0]
                            for i, part in enumerate(parts[1:], 1):
                                reconstructed += ' \\\n    --' + part
                            processed_lines.append(reconstructed)
                        else:
                            processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            
            processed_code = '\n'.join(processed_lines)
            return f'```{lang}\n{processed_code}\n```'
        
        # Apply the replacement
        content = re.sub(fenced_pattern, replace_fenced_code, content, flags=re.DOTALL)
        
        return content

def open_report_url(self):
    """
    Open the GitHub issues page for reporting bugs or feature requests.
    """
    try:
        webbrowser.open("https://github.com/Axel-Nahum/NanoVNA-UTN-Toolkit")
    except Exception as e:
        # Fallback if webbrowser fails
        QMessageBox.information(
            self, 
            "Report Issues", 
            "Please visit: https://github.com/Axel-Nahum/NanoVNA-UTN-Toolkit\n"
            "to report bugs or request features."
        )

def show_about_dialog(self, language='en'):
    """
    Show the About dialog with the project README.
    
    Args:
        language: Language code ('en' for English, 'es' for Spanish)
    """
    try:
        about_dialog = AboutDialog(self, language)
        about_dialog.exec()
    except Exception as e:
        # Fallback if dialog creation fails
        if language == 'es':
            QMessageBox.about(
                self,
                "Acerca de NanoVNA UTN Toolkit",
                "NanoVNA UTN Toolkit\n\n"
                "Un toolkit integral para mediciones y análisis con NanoVNA.\n\n"
                "UTN FRBA 2025 - MEDIDAS ELECTRÓNICAS II - Curso R5052\n\n"
                "Para más información, visite:\n"
                "https://github.com/fcascan/NanoVNA-UTN-Toolkit"
            )
        else:
            QMessageBox.about(
                self,
                "About NanoVNA UTN Toolkit",
                "NanoVNA UTN Toolkit\n\n"
                "A comprehensive toolkit for NanoVNA measurements and analysis.\n\n"
                "UTN FRBA 2025 - ELECTRONIC MEASUREMENTS II - Course R5052\n\n"
                "For more information, visit:\n"
                "https://github.com/fcascan/NanoVNA-UTN-Toolkit"
            )