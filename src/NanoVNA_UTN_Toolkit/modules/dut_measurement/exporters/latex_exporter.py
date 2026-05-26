"""
LaTeX PDF Exporter for NanoVNA measurement data.

This module provides functionality to export S-parameter data to PDF using LaTeX.
"""

import os
import sys
import tempfile
import subprocess
import shutil
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from datetime import datetime
import skrf as rf
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QFileDialog
from pylatex import Document, Section, Subsection, Command, Figure, NewPage
from pylatex.utils import NoEscape

# Set up logging
logger = logging.getLogger(__name__)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------------ #

def _find_latex_compiler():
    """
    Find available LaTeX compiler on the system.
    
    Returns:
        tuple: (compiler_name, full_path) or (None, None) if not found
    """
    # List of possible LaTeX compilers to try
    compilers = ['pdflatex', 'xelatex', 'lualatex']
    
    # First check system PATH
    for compiler in compilers:
        if shutil.which(compiler):
            return compiler, compiler  # Return name and path (same if in PATH)
    
    # On Windows, check common MikTeX paths
    if os.name == 'nt':
        common_paths = [
            r'C:\Program Files\MiKTeX\miktex\bin\x64',
            r'C:\Program Files (x86)\MiKTeX\miktex\bin',
            r'C:\Users\{}\AppData\Local\Programs\MiKTeX\miktex\bin\x64'.format(os.getenv('USERNAME', '')),
            r'C:\texlive\2023\bin\win32',
            r'C:\texlive\2022\bin\win32',
            r'C:\texlive\2021\bin\win32'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                for compiler in compilers:
                    compiler_path = os.path.join(path, compiler + '.exe')
                    if os.path.exists(compiler_path):
                        return compiler, compiler_path  # Return name and full path
    
    return None, None


def _test_latex_compiler(compiler_path):
    """
    Test if the LaTeX compiler is working properly.
    
    Args:
        compiler_path: Full path to the compiler executable
        
    Returns:
        bool: True if compiler works, False otherwise
    """
    try:
        # Create a simple test document
        test_content = r"""
\documentclass{article}
\begin{document}
Test
\end{document}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.tex")
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            # Try to compile using full path
            result = subprocess.run(
                [compiler_path, "-interaction=nonstopmode", "test.tex"],
                cwd=temp_dir,
                capture_output=True,
                timeout=30, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


class LatexExporter:
    """
    Exports NanoVNA measurement data to PDF using LaTeX.
    
    Creates a professional PDF report with:
    - Cover page with project information
    - S11 section: Magnitude, Phase, Smith Chart
    - S21 section: Magnitude, Phase
    """
    
    def __init__(self, measurement_self = None, parent_widget=None, figures=None):
        """
        Initialize the LaTeX exporter.
        
        Args:
            parent_widget: Parent widget for dialog boxes (optional)
        """
        self.parent_widget = parent_widget
        self.measurement_self = measurement_self

        self.figures = figures
    
    def check_latex_installation(self):
        """
        Check if LaTeX is properly installed and working.
        
        Returns:
            tuple: (is_available, compiler_info, error_message)
        """
        compiler_name, compiler_path = _find_latex_compiler()
        if compiler_name is None:
            return False, None, "No LaTeX compiler found. Please install MikTeX, TeX Live, or another LaTeX distribution."
        
        if not _test_latex_compiler(compiler_path):
            return False, (compiler_name, compiler_path), f"LaTeX compiler '{compiler_name}' found but not working properly. Please check your LaTeX installation."
        
        return True, (compiler_name, compiler_path), None
    
    def export_to_pdf(self, freqs, s11_data, s21_data, measurement_name=None, output_path=None):
        """
        Export S-parameter data to PDF using LaTeX.

        Args:
            freqs: Frequency array in Hz
            s11_data: S11 parameter data (complex array)
            s21_data: S21 parameter data (complex array)
            measurement_name: Optional measurement name for the report
            output_path: Path where the PDF should be saved

        Returns:
            bool: True if export successful, False otherwise
        """

        if self.figures and len(self.figures) > 0:
            if output_path is None:
                filename, _ = QFileDialog.getSaveFileName(
                    self.parent_widget,
                    "Export LaTeX PDF",
                    "",
                    "PDF Files (*.pdf)"
                )
                if not filename:
                    return False
                file_path = Path(filename).with_suffix('')
            else:
                file_path = Path(output_path).with_suffix('')

            # Asegurarse de tener un compilador LaTeX válido
            is_available, compiler_info, error_msg = self.check_latex_installation()
            if not is_available:
                self._show_error("LaTeX Installation Error", error_msg)
                return False
            compiler_path = compiler_info[1]

            with tempfile.TemporaryDirectory() as tmpdirname:
                image_files = self._generate_plots_from_figures(self.figures, tmpdirname)
                self._create_latex_document_with_compiler(
                    freqs=freqs,
                    image_files=image_files,
                    file_path=file_path,
                    tmpdirname=tmpdirname,
                    measurement_name=measurement_name,
                    vna_name="NanoVNA",
                    specific_compiler_path=compiler_path
                )
            return True
        else:
            if freqs is None or s11_data is None or s21_data is None:
                self._show_warning("Missing Data", "S11, S21 or frequencies are not available.")
                return False

            # Check LaTeX installation before proceeding
            is_available, compiler_info, error_msg = self.check_latex_installation()
            if not is_available:
                self._show_error("LaTeX Installation Error", error_msg)
                return False

            # Use the provided output path or ask the user for a location
            if output_path is None:
                filename, _ = QFileDialog.getSaveFileName(
                    self.parent_widget, 
                    "Export LaTeX PDF", 
                    "", 
                    "PDF Files (*.pdf)"
                )
                if not filename:
                    return False
                file_path = Path(filename).with_suffix('')
            else:
                file_path = Path(output_path).with_suffix('')

            pdf_path = str(file_path) + ".pdf"

            try:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    image_files = self._generate_plots(freqs, s11_data, s21_data, tmpdirname)
                    self._create_latex_document(freqs, image_files, file_path, tmpdirname, file_path.name, measurement_name)

                self._show_info("Success", f"LaTeX PDF exported successfully to:\n{pdf_path}")
                return True

            except Exception as e:
                self._show_error("Error generating LaTeX PDF", str(e))
                return False
    
    def export_to_pdf_with_dialog(self, freqs, s11_data, s21_data, measurement_name=None):
        """
        Export S-parameter data to PDF using LaTeX with pre-export dialog.
        
        This method shows a dialog that:
        - Checks LaTeX installation
        - Allows path selection
        - Validates setup before proceeding
        
        Args:
            freqs: Frequency array in Hz
            s11_data: S11 parameter data (complex array)
            s21_data: S21 parameter data (complex array)
            measurement_name: Optional measurement name for the report
            
        Returns:
            bool: True if export successful, False otherwise
        """
        logger.info("Starting LaTeX PDF export with dialog")
        
        if freqs is None or s11_data is None or s21_data is None:
            logger.warning("Export cancelled: missing required data")
            self._show_warning("Missing Data", "S11, S21 or frequencies are not available.")
            return False

        try:
            # Import the dialog (lazy import to avoid circular dependencies)
            from NanoVNA_UTN_Toolkit.modules.dut_measurement.exporters.export.latex_export_dialog import LaTeXExportDialog
            
            # Create and show the dialog
            default_filename = measurement_name if measurement_name else "nanovna_report"
            dialog = LaTeXExportDialog(measurement_self = self.measurement_self, parent=self.parent_widget, default_filename = default_filename)
            
            logger.info(f"Showing LaTeX export dialog with default filename: {default_filename}")
            
            if dialog.exec() != 1:  # QDialog.Accepted = 1
                logger.info("LaTeX export cancelled by user")
                return False
            
            # Get the selected output path
            output_path = dialog.get_output_path()
            if not output_path:
                logger.error("No output path selected")
                self._show_error("Export Error", "No output path was selected.")
                return False
            
            logger.info(f"Output path selected: {output_path}")
            
            # Verify LaTeX is still available (should be, but double-check)
            if not dialog.is_latex_available():
                logger.error("LaTeX not available for export")
                self._show_error("LaTeX Error", "LaTeX compiler is not available.")
                return False
            
            # Proceed with the export using the selected path and compiler
            file_path = Path(output_path).with_suffix('')
            pdf_path = str(file_path) + ".pdf"
            
            # Get the selected compiler from the dialog
            selected_compiler_path = dialog.get_compiler_path()
            
            logger.info(f"Starting PDF generation to: {pdf_path}")
            logger.info(f"Using compiler: {selected_compiler_path}")
            
            with tempfile.TemporaryDirectory() as tmpdirname:
                logger.debug("Generating plots for PDF")
                image_files = self._generate_plots(freqs, s11_data, s21_data, tmpdirname)
                
                logger.debug("Creating LaTeX document")
                self._create_latex_document_with_compiler(freqs, image_files, file_path, tmpdirname, file_path.name, measurement_name, selected_compiler_path)

            logger.info(f"LaTeX PDF export completed successfully: {pdf_path}")
            self._show_info("Success", f"LaTeX PDF exported successfully to:\\n{pdf_path}")
            return True

        except ImportError as e:
            logger.error(f"Failed to import LaTeX export dialog: {e}")
            self._show_error("Import Error", "Failed to load LaTeX export dialog. Using fallback method.")
            # Fallback to original method
            return self.export_to_pdf(freqs, s11_data, s21_data, measurement_name)
        except Exception as e:
            logger.error(f"Error during LaTeX export with dialog: {e}")
            self._show_error("Error generating LaTeX PDF", str(e))
            return False
    
    def _generate_plots(self, freqs, s11_data, s21_data, output_dir):
        """
        Generate all required plots for the PDF report.
        
        Args:
            freqs: Frequency array
            s11_data: S11 data
            s21_data: S21 data
            output_dir: Directory to save plot images
            
        Returns:
            dict: Dictionary mapping plot names to file paths
        """
        image_files = {}

        # Smith Diagram
        fig, ax = plt.subplots(figsize=(10, 10))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ntw = rf.Network(frequency=freqs, s=s11_data[:, np.newaxis, np.newaxis], z0=50)
        ntw.plot_s_smith(ax=ax, draw_labels=True)
        ax.legend([Line2D([0], [0], color='blue')], ['S11'], loc='upper left', bbox_to_anchor=(-0.17, 1.14))
        smith_path = os.path.join(output_dir, "smith.png")
        fig.savefig(smith_path, dpi=300)
        plt.close(fig)
        image_files['smith'] = smith_path

        # Magnitude S11
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.plot(freqs * 1e-6, 20 * np.log10(np.abs(s11_data)), color='blue')
        ax.set_xlabel("Frequency [MHz]")
        ax.set_ylabel("|S11|")
        ax.set_title("Magnitude S11")
        ax.grid(True, linestyle='--', alpha=0.5)
        mag_s11_path = os.path.join(output_dir, "magnitude_s11.png")
        fig.savefig(mag_s11_path, dpi=300)
        plt.close(fig)
        image_files['mag_s11'] = mag_s11_path

        # Phase S11
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.plot(freqs * 1e-6, np.angle(s11_data, deg=True), color='blue')
        ax.set_xlabel("Frequency [MHz]")
        ax.set_ylabel("Phase S11 [deg]")
        ax.set_title("Phase S11")
        ax.grid(True, linestyle='--', alpha=0.5)
        phase_s11_path = os.path.join(output_dir, "phase_s11.png")
        fig.savefig(phase_s11_path, dpi=300)
        plt.close(fig)
        image_files['phase_s11'] = phase_s11_path

        # Magnitude S21
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.plot(freqs * 1e-6, 20 * np.log10(np.abs(s21_data)), color='red')
        ax.set_xlabel("Frequency [MHz]")
        ax.set_ylabel("|S21|")
        ax.set_title("Magnitude S21")
        ax.grid(True, linestyle='--', alpha=0.5)
        mag_s21_path = os.path.join(output_dir, "magnitude_s21.png")
        fig.savefig(mag_s21_path, dpi=300)
        plt.close(fig)
        image_files['mag_s21'] = mag_s21_path

        # Phase S21
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.plot(freqs * 1e-6, np.angle(s21_data, deg=True), color='red')
        ax.set_xlabel("Frequency [MHz]")
        ax.set_ylabel("Phase S21 [deg]")
        ax.set_title("Phase S21")
        ax.grid(True, linestyle='--', alpha=0.5)
        phase_s21_path = os.path.join(output_dir, "phase_s21.png")
        fig.savefig(phase_s21_path, dpi=300)
        plt.close(fig)
        image_files['phase_s21'] = phase_s21_path

        return image_files
    
    def _create_latex_document(self, freqs, image_files, file_path, tmpdirname, measurement_name, vna_name):
        """
        Create the LaTeX document with all sections and images.
        
        Args:
            image_files: Dictionary of image file paths
            file_path: Output file path
            tmpdirname: Temporary directory name
            measurement_name: Name of the measurement
        """
        doc = Document(
            documentclass='article',
            document_options='12pt',
            geometry_options={'paper': 'a4paper', 'margin': '2cm'}
        )
        doc.preamble.append(Command('usepackage', 'graphicx'))

        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Read calibration info from config
        calibration_method, calibrated_parameter, measurement_number = self._get_calibration_info(
            measurement_name
        )

        # Cover page
        self._create_cover_page(doc, freqs=freqs, current_datetime=current_datetime,
                                measurement_name=measurement_name,
                                measurement_number=measurement_number, 
                                calibration_method=calibration_method,
                                calibrated_parameter=calibrated_parameter,
                                vna_name=vna_name)


        # S11 Section
        s11_images = {
            "Magnitude": "mag_s11",
            "Phase": "phase_s11",
            "Smith Diagram": "smith"
        }
        with doc.create(Section("S11")):
            for subname, key in s11_images.items():
                with doc.create(Subsection(subname)):
                    doc.append(NoEscape(r'\begin{center}'))
                    doc.append(NoEscape(r'\includegraphics[width=0.8\linewidth]{' +
                                        image_files[key].replace("\\", "/") + '}'))
                    doc.append(NoEscape(r'\end{center}'))

        # S21 Section
        s21_images = {
            "Magnitude": "mag_s21",
            "Phase": "phase_s21"
        }
        with doc.create(Section("S21")):
            for subname, key in s21_images.items():
                with doc.create(Subsection(subname)):
                    doc.append(NoEscape(r'\begin{center}'))
                    doc.append(NoEscape(r'\includegraphics[width=0.8\linewidth]{' +
                                        image_files[key].replace("\\", "/") + '}'))
                    doc.append(NoEscape(r'\end{center}'))

        # Generate PDF with automatic compiler detection
        compiler_name, compiler_path = _find_latex_compiler()
        if compiler_name is None or compiler_path is None:
            raise Exception("No LaTeX compiler found. Please install MikTeX, TeX Live, or another LaTeX distribution.")
        
        if not _test_latex_compiler(compiler_path):
            raise Exception(f"LaTeX compiler '{compiler_name}' found but not working properly. Please check your LaTeX installation.")
        
        try:
            # If we have a full path, use just the compiler name for pylatex
            # and modify the PATH temporarily
            if os.path.isabs(compiler_path):
                # Add the compiler directory to PATH temporarily
                original_path = os.environ.get('PATH', '')
                compiler_dir = os.path.dirname(compiler_path)
                os.environ['PATH'] = compiler_dir + os.pathsep + original_path
                
                try:
                    doc.generate_pdf(str(file_path), compiler=compiler_name, clean_tex=False)
                finally:
                    # Restore original PATH
                    os.environ['PATH'] = original_path
            else:
                # Compiler is in PATH, use normally
                doc.generate_pdf(str(file_path), compiler=compiler_name, clean_tex=False)
        except Exception as e:
            raise Exception(f"Failed to generate PDF with {compiler_name}: {str(e)}. Please check your LaTeX installation and ensure all required packages are installed.")
    
    def _create_latex_document_with_compiler(self, freqs, image_files, file_path, tmpdirname, measurement_name, vna_name, specific_compiler_path):
        """
        Create the LaTeX document with cover page and all images using a specific compiler.

        Args:
            freqs: Frequency array (can be None)
            image_files: Dictionary of image file paths
            file_path: Output file path
            tmpdirname: Temporary directory name
            measurement_name: Name of the measurement
            vna_name: VNA device name
            specific_compiler_path: Full path to the LaTeX compiler to use
        """
        doc = Document(
            documentclass='article',
            document_options='12pt',
            geometry_options={'paper': 'a4paper', 'margin': '2cm'}
        )
        doc.preamble.append(Command('usepackage', 'graphicx'))

        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        calibration_method, calibrated_parameter, measurement_number = self._get_calibration_info(measurement_name)

        # --- COVER PAGE ---
        self._create_cover_page(doc, freqs=freqs, current_datetime=current_datetime,
                                measurement_name=measurement_name,
                                measurement_number=measurement_number,
                                calibration_method=calibration_method,
                                calibrated_parameter=calibrated_parameter,
                                vna_name=vna_name)

        # --- PAGES WITH IMAGES ---
        doc.append(NewPage())  # Start from the second page
        with doc.create(Section("Measurement Graphs")):
            keys = list(image_files.keys())
            paths = list(image_files.values())

            # --- Smith chart alone on first page ---
            with doc.create(Figure(position='h!')) as fig:
                fig.add_image(paths[0].replace("\\", "/"), width=NoEscape(r'0.8\linewidth'))
            doc.append(NewPage())

            # --- Second and third images stacked vertically on one page ---
            if len(paths) >= 3:
                with doc.create(Figure(position='h!')) as fig:
                    fig.add_image(paths[1].replace("\\", "/"), width=NoEscape(r'0.8\linewidth'))
                doc.append(NoEscape(r'\vspace{1cm}'))  # spacing between the two images
                with doc.create(Figure(position='h!')) as fig:
                    fig.add_image(paths[2].replace("\\", "/"), width=NoEscape(r'0.8\linewidth'))
                doc.append(NewPage())

            # --- Fourth and fifth images stacked vertically on one page ---
            if len(paths) >= 5:
                with doc.create(Figure(position='h!')) as fig:
                    fig.add_image(paths[3].replace("\\", "/"), width=NoEscape(r'0.8\linewidth'))
                doc.append(NoEscape(r'\vspace{1cm}'))
                with doc.create(Figure(position='h!')) as fig:
                    fig.add_image(paths[4].replace("\\", "/"), width=NoEscape(r'0.8\linewidth'))
                doc.append(NewPage())


        # --- GENERATE PDF USING SPECIFIC COMPILER ---
        compiler_name = os.path.basename(specific_compiler_path).replace('.exe', '')
        original_path = os.environ.get('PATH', '')
        os.environ['PATH'] = os.path.dirname(specific_compiler_path) + os.pathsep + original_path
        try:
            logger.info(f"Generating PDF using specific compiler: {compiler_name}")
            doc.generate_pdf(str(file_path), compiler=compiler_name, clean_tex=False)
        finally:
            os.environ['PATH'] = original_path
    
    def _create_cover_page(self, doc, freqs, current_datetime, measurement_name, measurement_number, 
                          calibration_method, calibrated_parameter, vna_name):

        # Load configuration for calibration settings
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini", 
            Path(__file__).resolve()
        )
        
        kits_ok = settings_calibration.value("Calibration/Kits", False, type=bool)
        selected_kit = settings_calibration.value("Calibration/Name", "Normalization")
        kit_id = settings_calibration.value("Calibration/id", 0)
        kit_name_only = selected_kit.rsplit("_", 1)[0]
        kit_name_only_tex = kit_name_only.replace("_", r"\_")

        no_calibration = settings_calibration.value("Calibration/NoCalibration", False, type=bool)
        is_import_dut = settings_calibration.value("Calibration/DUT", False, type=bool)

        # Load configuration for sweep settings and frequency range parameters
        settings_sweep = get_settings(
            "INI/dut_measurement/sweep_config/sweep_config.ini",
            "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini", 
            Path(__file__).resolve()        
        )

        start_unit = settings_sweep.value("Frequency/StartUnit", "MHz")
        stop_unit = settings_sweep.value("Frequency/StopUnit", "MHz")

        def unit_and_scale_per_value(f_hz):
            if f_hz < 1e3:
                return "Hz", 1
            elif f_hz < 1e6:
                return "kHz", 1e3
            elif f_hz < 1e9:
                return "MHz", 1e6
            else:
                return "GHz", 1e9
        
        scaled_freqs = []
        units = []

        u, s = unit_and_scale_per_value(freqs[0])
        scaled_freqs.append(freqs[0] / s)
        units.append(u)

        u, s = unit_and_scale_per_value(freqs[-1])
        scaled_freqs.append(freqs[-1] / s)
        units.append(u)

        if freqs is not None:
            start_freq = freqs[0]
            stop_freq = freqs[-1]
            if start_unit == "KHz":
                start_freq /= 1e3
            elif start_unit == "MHz":
                start_freq /= 1e6
            elif start_unit == "GHz":
                start_freq /= 1e9
            if stop_unit == "kHz":
                stop_freq /= 1e3
            elif stop_unit == "MHz":
                stop_freq /= 1e6
            elif stop_unit == "GHz":
                stop_freq /= 1e9
        else:
            start_freq = "N/A"
            stop_freq = "N/A"

        """Create the cover page for the PDF."""
        doc.append(NoEscape(r'\begin{titlepage}'))
        doc.append(NoEscape(r'\begin{center}'))

        doc.append(NoEscape(r'\vspace*{2cm}'))
        doc.append(NoEscape(r'\Huge \textbf{NanoVNA Report} \\[1.2cm]'))
        doc.append(NoEscape(r'\LARGE NanoVNA UTN Toolkit \\[0.8cm]'))
        doc.append(NoEscape(r'\large ' + current_datetime))

        doc.append(NoEscape(r'\vspace{3cm}'))
        doc.append(NoEscape(r'\begin{flushleft}'))
        doc.append(NoEscape(r'\Large \textbf{Measurement Details:} \\[0.5cm]'))
        doc.append(NoEscape(r'\normalsize'))
        doc.append(NoEscape(r'\begin{itemize}'))
        doc.append(NoEscape(rf'\item \textbf{{Measurement Name:}} {measurement_name}'))
        doc.append(NoEscape(rf'\item \textbf{{Measurement Number:}} {measurement_number}'))

        if kits_ok and not no_calibration and not is_import_dut:
            date_time_calibration = settings_calibration.value("Calibration/DateTime_Kits", "1")
            date_time_type = "Kit"
            doc.append(NoEscape(rf'\item \textbf{{Selected kit:}} {kit_name_only_tex}'))
            doc.append(NoEscape(rf'\item \textbf{{Calibration Kit Method:}} {calibration_method}'))
            doc.append(NoEscape(rf'\item \textbf{{Calibrated Parameter:}} {calibrated_parameter}'))
        elif not kits_ok and not no_calibration and not is_import_dut:
            date_time_calibration = settings_calibration.value("Calibration/DateTime_Calibration", "1")
            date_time_type = "Calibration"
            doc.append(NoEscape(rf'\item \textbf{{Calibration Wizard Method:}} {calibration_method}'))
            doc.append(NoEscape(rf'\item \textbf{{Calibrated Parameter:}} {calibrated_parameter}'))
        elif not kits_ok and no_calibration and not is_import_dut:
            date_time_calibration = current_datetime
            date_time_type = "No Calibration"
            doc.append(NoEscape(r'\item \textbf{{No Calibration}}'))
        elif is_import_dut:
            date_time_calibration = current_datetime
            date_time_type = "Dut"
            doc.append(NoEscape(r'\item \textbf{{DUT}}'))
            settings_calibration.setValue("Calibration/DUT", False)

        if kits_ok or not kits_ok and not no_calibration and not is_import_dut:
            doc.append(NoEscape(rf'\item \textbf{{Date and Time ({date_time_type}):}} {date_time_calibration}'))

        doc.append(NoEscape(r'\end{itemize}'))
        doc.append(NoEscape(r'\end{flushleft}'))

        doc.append(NoEscape(r'\begin{flushleft}'))
        doc.append(NoEscape(r'\Large \textbf{Instrument Details:} \\[0.5cm]'))
        doc.append(NoEscape(r'\normalsize'))
        doc.append(NoEscape(r'\begin{itemize}')) 
        doc.append(NoEscape(rf'\item \textbf{{VNA:}} {vna_name}'))
        doc.append(NoEscape(rf'\item \textbf{{Frequency Range:}} {scaled_freqs[0]} {units[0]} - {scaled_freqs[-1]} {units[-1]}'))
        doc.append(NoEscape(rf'\item \textbf{{Normalization Impedance:}} 50 \textohm'))
        doc.append(NoEscape(r'\end{itemize}')) 
        doc.append(NoEscape(r'\end{flushleft}'))

        doc.append(NoEscape(r'\end{center}'))
        doc.append(NoEscape(r'\end{titlepage}'))

    def _get_calibration_info(self, measurement_name):
        """
        Get calibration information from config files.
        
        Args:
            measurement_name: Name of the measurement
            
        Returns:
            tuple: (calibration_method, calibrated_parameter, measurement_number)
        """
        try:
            # Note: This assumes a specific directory structure relative to UI
            # In a real application, you might want to make this configurable

            # Load configuration for calibration settings
            settings = get_settings(
                "INI/dut_measurement/calibration_config/calibration_config.ini",
                "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                Path(__file__).resolve()
            )

            calibration_method = settings.value("Calibration/Method", "---")
            calibrated_parameter = settings.value("Calibration/Parameter", "---")

            # Handle measurement numbering with daily reset
            measurement_number = 1
            
            # Load configuration for measurement
            tracking_settings = get_settings(
                "INI/dut_measurement/measurement_numbers/measurement_numbers.ini",
                "modules/dut_measurement/calibration/measurement_numbers/measurement_numbers.ini", 
                Path(__file__).resolve()
            )

            # Get current date as string (YYYY-MM-DD format)
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Check if we have a date stored and if it's different from today
            stored_date = tracking_settings.value("LastResetDate", "")
            
            # If the date has changed, reset all counters
            if stored_date != current_date:
                # Clear all existing measurement numbers
                tracking_settings.clear()
                # Store the new date
                tracking_settings.setValue("LastResetDate", current_date)
                measurement_number = 1
            else:
                # Same day, get current counter for this specific measurement name
                if tracking_settings.contains(measurement_name):
                    # This measurement name has been used today, increment its counter
                    measurement_number = int(tracking_settings.value(measurement_name)) + 1
                else:
                    # First time using this measurement name today
                    measurement_number = 1
            
            # Save the updated measurement number for this specific name
            tracking_settings.setValue(measurement_name, measurement_number)
            tracking_settings.sync()
                
            return calibration_method, calibrated_parameter, measurement_number
        except Exception:
            # Fallback values if config reading fails
            return "---", "---", 1
    
    def _show_warning(self, title, message):
        """Show warning message box."""
        if self.parent_widget:
            QMessageBox.warning(self.parent_widget, title, message)
    
    def _show_info(self, title, message):
        """Show information message box."""
        if self.parent_widget:
            QMessageBox.information(self.parent_widget, title, message)
    
    def _show_error(self, title, message):
        """Show error message box."""
        if self.parent_widget:
            QMessageBox.critical(self.parent_widget, title, message)

    def _generate_plots_from_figures(self, figures, output_dir):
        """
        Save existing Matplotlib figures as PNG for LaTeX PDF.
        
        Args:
            figures: list of matplotlib.figure.Figure
            output_dir: directory to save PNGs
        
        Returns:
            dict: mapping keys to file paths
        """
        image_files = {}
        for i, fig in enumerate(figures):
            path = os.path.join(output_dir, f"figure_{i}.png")
            fig.savefig(path, dpi=300)
            image_files[f"fig_{i}"] = path
        return image_files