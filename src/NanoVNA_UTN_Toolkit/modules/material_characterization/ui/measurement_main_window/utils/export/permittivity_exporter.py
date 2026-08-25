"""
LaTeX PDF Exporter for permittivity characterization data.

Mirrors the structure of the DUT latex_exporter.py: compiler detection,
PDF generation from saved preview figures, and a cover page with
characterization-specific metadata.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import os
import tempfile
import subprocess
import shutil
import logging
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_CHART_INI_EXE = "INI/material_characterization/characterization_chart_config/characterization_chart_config.ini"
_CHART_INI_DEV = "modules/material_characterization/ui/measurement_main_window/characterization_chart_config/characterization_chart_config.ini"

plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["text.usetex"] = False
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.rm"] = "serif"


# --------------------------------------------------------------------------- #
# Compiler detection (identical to DUT module)
# --------------------------------------------------------------------------- #

def _find_latex_compiler():
    """Find an available LaTeX compiler on the system."""
    compilers = ["pdflatex", "xelatex", "lualatex"]
    for compiler in compilers:
        if shutil.which(compiler):
            return compiler, compiler
    if os.name == "nt":
        common_paths = [
            r"C:\Program Files\MiKTeX\miktex\bin\x64",
            r"C:\Program Files (x86)\MiKTeX\miktex\bin",
            r"C:\Users\{}\AppData\Local\Programs\MiKTeX\miktex\bin\x64".format(
                os.getenv("USERNAME", "")
            ),
            r"C:\texlive\2023\bin\win32",
            r"C:\texlive\2022\bin\win32",
            r"C:\texlive\2021\bin\win32",
        ]
        for path in common_paths:
            if os.path.exists(path):
                for compiler in compilers:
                    compiler_path = os.path.join(path, compiler + ".exe")
                    if os.path.exists(compiler_path):
                        return compiler, compiler_path
    return None, None


def _test_latex_compiler(compiler_path):
    """Return True if the given LaTeX compiler can compile a trivial document."""
    try:
        test_content = r"\documentclass{article}\begin{document}Test\end{document}"
        with tempfile.TemporaryDirectory() as tmp:
            test_file = os.path.join(tmp, "test.tex")
            with open(test_file, "w") as f:
                f.write(test_content)
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                [compiler_path, "-interaction=nonstopmode", "test.tex"],
                cwd=tmp, capture_output=True, timeout=30, **kwargs,
            )
            return result.returncode == 0
    except Exception:
        return False


# --------------------------------------------------------------------------- #

def _fill_nans(y: np.ndarray) -> np.ndarray:
    finite = np.isfinite(y)
    if finite.all() or not finite.any():
        return y
    x = np.arange(len(y))
    out = y.copy()
    out[~finite] = np.interp(x[~finite], x[finite], y[finite])
    return out


def _freq_scale(freqs):
    max_f = float(np.max(freqs))
    if max_f >= 0.5e9:
        return 1e9, "GHz"
    if max_f >= 0.5e6:
        return 1e6, "MHz"
    return 1e3, "kHz"


# --------------------------------------------------------------------------- #

class PermittivityExporter:
    """Exports characterization results (S11 Smith + permittivity) to PDF via LaTeX."""

    def __init__(self, parent_widget=None, figures=None):
        self.parent_widget = parent_widget
        self.figures = figures  # list of matplotlib figures from the preview dialog

    # ------------------------------------------------------------------ #

    def check_latex_installation(self):
        """Return (is_available, compiler_info, error_message)."""
        compiler_name, compiler_path = _find_latex_compiler()
        if compiler_name is None:
            return (
                False, None,
                "No LaTeX compiler found.\nPlease install MikTeX or TeX Live.",
            )
        if not _test_latex_compiler(compiler_path):
            return (
                False,
                (compiler_name, compiler_path),
                f"LaTeX compiler '{compiler_name}' found but not working properly.",
            )
        return True, (compiler_name, compiler_path), None

    # ------------------------------------------------------------------ #

    def render_images(self, freqs, s11_data, eps_selected, output_dir,
                      wizard_window=None, include_steps=False):
        """Rasterize every figure into ``output_dir``.  Uses self.figures if available.

        Must run on the UI thread: matplotlib is not thread-safe.
        """
        if self.figures:
            image_files = self._generate_plots_from_figures(self.figures, output_dir)
        else:
            image_files = self._generate_plots(freqs, s11_data, eps_selected, output_dir)

        if include_steps and wizard_window is not None:
            image_files.update(self._render_step_charts(wizard_window, output_dir))

        return image_files

    def compile_pdf(
        self, freqs, eps_selected, image_files, sample_name,
        wizard_window, output_path, compiler_path, include_steps=False,
    ):
        """Build the .tex from already-rendered images and run LaTeX.

        Blocking and Qt-free, so it can be handed to a worker thread. Raises on
        failure instead of showing a dialog.
        """
        self._create_latex_document(
            freqs=freqs,
            eps_selected=eps_selected,
            image_files=image_files,
            file_path=Path(output_path).with_suffix(""),
            sample_name=sample_name,
            wizard_window=wizard_window,
            compiler_path=compiler_path,
            include_steps=include_steps,
        )

    def export_to_pdf(
        self, freqs, s11_data, eps_selected, sample_name,
        wizard_window, output_path, compiler_path,
    ):
        """Render and compile in one blocking call (freezes the UI while it runs).

        Kept for callers that do not drive the two steps themselves; the preview
        dialog splits them so the compilation can run off the UI thread.
        """
        try:
            with tempfile.TemporaryDirectory() as tmp:
                image_files = self.render_images(freqs, s11_data, eps_selected, tmp)
                self.compile_pdf(
                    freqs=freqs,
                    eps_selected=eps_selected,
                    image_files=image_files,
                    sample_name=sample_name,
                    wizard_window=wizard_window,
                    output_path=output_path,
                    compiler_path=compiler_path,
                )
            return True
        except Exception as exc:
            logger.error("[PermittivityExporter] export failed: %s", exc)
            if self.parent_widget:
                QMessageBox.critical(
                    self.parent_widget, "Export Error",
                    f"Failed to generate PDF:\n{exc}",
                )
            return False

    # ------------------------------------------------------------------ #

    def _generate_plots_from_figures(self, figures, output_dir):
        """Save existing preview figures as high-DPI PNGs for LaTeX inclusion."""
        image_files = {}
        keys = ["smith", "permittivity"]
        for i, fig in enumerate(figures):
            key = keys[i] if i < len(keys) else f"fig_{i}"
            path = os.path.join(output_dir, f"{key}.png")
            fig.savefig(path, dpi=300, bbox_inches="tight")
            image_files[key] = path
        return image_files

    # ------------------------------------------------------------------ #

    def _generate_plots(self, freqs, s11_data, eps_selected, output_dir):
        """Fallback: render Smith + permittivity directly from data (no preview figures)."""
        image_files = {}

        try:
            _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
            real_color = _s.value("Epsilon_Real/TraceColor", "#1f77b4")
            loss_color = _s.value("Epsilon_Imag/TraceColor", "#d62728")
        except Exception:
            real_color, loss_color = "#1f77b4", "#d62728"

        # --- Smith S11 ---
        try:
            import skrf as rf
            fig, ax = plt.subplots(figsize=(7, 7))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            f_arr = np.asarray(freqs, dtype=float)
            dummy_freq = rf.Frequency(f_arr[0] / 1e9, f_arr[-1] / 1e9, len(f_arr), unit="GHz")
            dummy_s = np.zeros((len(f_arr), 1, 1), dtype=complex)
            dummy_s[:, 0, 0] = np.asarray(s11_data, dtype=complex)
            ntw = rf.Network(frequency=dummy_freq, s=dummy_s)
            ntw.plot_s_smith(ax=ax, draw_labels=True, color="red", lw=1.5, label=r"$S_{11}$")
            ax.set_title(r"$S_{11}$ — Smith Chart", fontsize=14, pad=10)
            ax.set_aspect("equal")
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            smith_path = os.path.join(output_dir, "smith.png")
            fig.savefig(smith_path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            image_files["smith"] = smith_path
        except Exception as exc:
            logger.error("[PermittivityExporter] Smith plot failed: %s", exc)

        # --- Permittivity ---
        f_arr = np.asarray(freqs, dtype=float)
        eps = np.asarray(eps_selected, dtype=complex)
        real = _fill_nans(np.real(eps))
        loss = _fill_nans(-np.imag(eps))
        div, unit = _freq_scale(f_arr)

        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.plot(f_arr / div, real, color=real_color, linewidth=2, label=r"$\varepsilon_r'$")
        ax.plot(f_arr / div, loss, color=loss_color, linewidth=2, label=r"$\varepsilon_r''$")
        ax.set_xlabel(f"Frequency ({unit})", fontsize=12)
        ax.set_ylabel(r"$\varepsilon_r$", fontsize=12)
        ax.set_title(r"$\varepsilon_r$ vs Frequency", fontsize=14, pad=10)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper right", fontsize=11)
        perm_path = os.path.join(output_dir, "permittivity.png")
        fig.savefig(perm_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        image_files["permittivity"] = perm_path

        return image_files

    # ------------------------------------------------------------------ #

    def _render_step_charts(self, wizard_window, output_dir):
        """Render |S11| magnitude charts for each calibration standard."""
        _LABELS = {
            "open":  "Open",
            "short": "Short",
            "ref1":  "Reference 1",
            "ref2":  "Reference 2",
            "dut":   "Unknown Liquid (DUT)",
        }
        cal = getattr(wizard_window, "perm_calibration", None)
        if cal is None:
            return {}

        # Enhance ref labels with liquid name
        try:
            from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
                get_reference_liquid,
            )
            if cal.ref1_key:
                _LABELS["ref1"] = f"Reference 1 ({get_reference_liquid(cal.ref1_key).display_name})"
            if cal.ref2_key:
                _LABELS["ref2"] = f"Reference 2 ({get_reference_liquid(cal.ref2_key).display_name})"
        except Exception:
            pass

        image_files = {}
        for key, label in _LABELS.items():
            data = cal.get_measurement(key)
            if data is None:
                continue
            freqs_s, s11_s = np.asarray(data[0], dtype=float), np.asarray(data[1], dtype=complex)
            div, unit = _freq_scale(freqs_s)
            mag_db = 20 * np.log10(np.abs(s11_s) + 1e-15)

            fig, ax = plt.subplots(figsize=(7, 3))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            ax.plot(freqs_s / div, mag_db, color="#1a6bbf", linewidth=1.5)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=10)
            ax.set_ylabel(r"$|S_{11}|$ (dB)", fontsize=10)
            ax.set_title(f"{label} — $|S_{{11}}|$", fontsize=11, pad=8)
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.tight_layout()
            path = os.path.join(output_dir, f"step_{key}.png")
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            image_files[f"step_{key}"] = path
        return image_files

    # ------------------------------------------------------------------ #

    def _create_latex_document(
        self, freqs, eps_selected, image_files, file_path,
        sample_name, wizard_window, compiler_path, include_steps=False,
    ):
        try:
            from pylatex import Document, Section, Subsection, Command, Figure, NewPage
            from pylatex.utils import NoEscape
        except ImportError as exc:
            raise RuntimeError("pylatex is required for PDF export.") from exc

        doc = Document(
            documentclass="article",
            document_options="12pt",
            geometry_options={"paper": "a4paper", "margin": "2cm"},
        )
        doc.preamble.append(Command("usepackage", "graphicx"))
        doc.preamble.append(Command("usepackage", "float"))
        doc.preamble.append(Command("usepackage", "textcomp"))
        doc.preamble.append(Command("usepackage", "longtable"))
        doc.preamble.append(Command("usepackage", "booktabs"))
        doc.preamble.append(Command("usepackage", "array"))

        current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._create_cover_page(doc, freqs, sample_name, wizard_window, current_dt)

        doc.append(NewPage())
        with doc.create(Section("Measurement Results")):
            # Smith S11
            if "smith" in image_files:
                with doc.create(Subsection(NoEscape(r"$S_{11}$ \textemdash{} Smith Chart"))):
                    with doc.create(Figure(position="H")) as fig_latex:
                        fig_latex.add_image(
                            image_files["smith"].replace("\\", "/"),
                            width=NoEscape(r"0.65\linewidth"),
                        )
                doc.append(NewPage())

            # Permittivity
            if "permittivity" in image_files:
                with doc.create(Subsection(NoEscape(
                    r"Complex Permittivity $\varepsilon_r(f)$"
                ))):
                    with doc.create(Figure(position="H")) as fig_latex:
                        fig_latex.add_image(
                            image_files["permittivity"].replace("\\", "/"),
                            width=NoEscape(r"0.9\linewidth"),
                        )

            # Branch selection criterion
            with doc.create(Subsection("Branch Selection Criterion")):
                doc.append(NoEscape(
                    r"\begin{itemize}"
                    r"\item \textbf{Physical filter:} $\mathrm{Re}(\varepsilon) > 0$,"
                    r" $\mathrm{Im}(\varepsilon) \leq 1\times10^{-6}$"
                    r"\item \textbf{Traversal:} high $\rightarrow$ low frequency"
                    r"\item \textbf{Seed:} root with smallest $|\mathrm{Im}(\varepsilon)|$"
                    r" at the highest valid frequency"
                    r"\item \textbf{Tracking:} polynomial extrapolation (window\,5, order\,$\leq$2)"
                    r" + nearest-neighbour match"
                    r"\item \textbf{Ill-conditioned points} ($|S_{11}^{r_1} - S_{11}^{r_2}| < 0.01$)"
                    r" excluded as gaps (NaN)"
                    r"\end{itemize}"
                ))

        # Calibration standard measurements (optional)
        if include_steps:
            self._build_step_sections(doc, image_files, wizard_window, NoEscape, NewPage,
                                      Section, Subsection, Figure)

        # Data table page
        if eps_selected is not None and freqs is not None:
            doc.append(NewPage())
            with doc.create(Section("Permittivity Data Table")):
                self._build_data_table(doc, freqs, eps_selected)

        # Compile
        compiler_name = os.path.basename(compiler_path).replace(".exe", "")
        original_path = os.environ.get("PATH", "")
        compiler_dir = os.path.dirname(compiler_path)
        if compiler_dir:
            os.environ["PATH"] = compiler_dir + os.pathsep + original_path
        try:
            doc.generate_pdf(str(file_path), compiler=compiler_name, clean_tex=False)
        finally:
            os.environ["PATH"] = original_path

    # ------------------------------------------------------------------ #

    def _build_data_table(self, doc, freqs, eps_selected):
        """Append a longtable with Frequency / ε′ / ε″ / tan δ columns."""
        from pylatex.utils import NoEscape

        f_hz = np.asarray(freqs, dtype=float)
        eps  = np.asarray(eps_selected, dtype=complex)
        n    = len(f_hz)
        # At most 1000 rows in the PDF; stride to keep compile time reasonable
        stride = max(1, n // 1000)

        def _fv(v, decimals):
            return r"\textemdash{}" if not np.isfinite(v) else f"{v:.{decimals}f}"

        # Build the longtable as raw LaTeX for reliability
        rows_latex = []
        for i in range(0, n, stride):
            re_v   = float(np.real(eps[i]))
            loss_v = float(-np.imag(eps[i]))
            if re_v != 0.0 and np.isfinite(re_v) and np.isfinite(loss_v):
                tand_v = loss_v / re_v
            else:
                tand_v = float("nan")
            rows_latex.append(
                f"{f_hz[i]/1e6:.4f} & {_fv(re_v,4)} & {_fv(loss_v,4)} & {_fv(tand_v,5)} \\\\"
            )

        n_shown = len(rows_latex)
        note = (
            f"Showing {n_shown} of {n} points (every {stride} point)."
            if stride > 1 else f"All {n_shown} measurement points."
        )

        table_body = "\n".join([
            r"\begin{longtable}{>{\centering\arraybackslash}p{3.0cm}"
            r">{\centering\arraybackslash}p{2.6cm}"
            r">{\centering\arraybackslash}p{2.6cm}"
            r">{\centering\arraybackslash}p{2.8cm}}",
            r"\toprule",
            r"\textbf{Frequency (MHz)} & \textbf{$\varepsilon'$} & \textbf{$\varepsilon''$} & \textbf{tan\,$\delta$} \\",
            r"\midrule",
            r"\endhead",
            r"\midrule",
            r"\multicolumn{4}{r}{\footnotesize\itshape (continued on next page)} \\",
            r"\endfoot",
            r"\bottomrule",
            r"\endlastfoot",
        ] + rows_latex + [
            r"\end{longtable}",
        ])

        doc.append(NoEscape(
            r"\noindent\footnotesize\textit{" + note.replace(".", r".\@") + r"}"
            r"\normalsize\medskip"
        ))
        doc.append(NoEscape(table_body))

    # ------------------------------------------------------------------ #

    def _build_step_sections(self, doc, image_files, wizard_window,
                              NoEscape, NewPage, Section, Subsection, Figure):
        """Append one subsection per calibration standard: S11 chart + mini-table."""
        _KEYS = ["open", "short", "ref1", "ref2", "dut"]
        _LABELS = {
            "open":  "Open",
            "short": "Short",
            "ref1":  "Reference 1",
            "ref2":  "Reference 2",
            "dut":   "Unknown Liquid (DUT)",
        }
        cal = getattr(wizard_window, "perm_calibration", None)

        # Enhance ref labels
        try:
            from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
                get_reference_liquid,
            )
            if cal and cal.ref1_key:
                _LABELS["ref1"] = f"Reference 1 ({get_reference_liquid(cal.ref1_key).display_name})"
            if cal and cal.ref2_key:
                _LABELS["ref2"] = f"Reference 2 ({get_reference_liquid(cal.ref2_key).display_name})"
        except Exception:
            pass

        doc.append(NewPage())
        with doc.create(Section("Calibration Standard Measurements")):
            any_added = False
            for key in _KEYS:
                img_key = f"step_{key}"
                if img_key not in image_files:
                    continue
                if cal is None:
                    continue
                data = cal.get_measurement(key)
                if data is None:
                    continue

                label = _LABELS.get(key, key.capitalize())
                freqs_s = np.asarray(data[0], dtype=float)
                s11_s   = np.asarray(data[1], dtype=complex)
                div, unit = _freq_scale(freqs_s)
                n = len(freqs_s)
                stride = max(1, n // 8)

                with doc.create(Subsection(label)):
                    with doc.create(Figure(position="H")) as fig_latex:
                        fig_latex.add_image(
                            image_files[img_key].replace("\\", "/"),
                            width=NoEscape(r"0.85\linewidth"),
                        )

                    # Mini-table: Frequency | Re(S11) | Im(S11) | |S11| dB
                    rows_tex = []
                    for i in range(0, n, stride):
                        f_val  = freqs_s[i] / div
                        re_val = float(np.real(s11_s[i]))
                        im_val = float(np.imag(s11_s[i]))
                        db_val = 20 * np.log10(abs(complex(re_val, im_val)) + 1e-15)
                        rows_tex.append(
                            f"{f_val:.3f} & {re_val:.4f} & {im_val:+.4f} & {db_val:.2f} \\\\"
                        )

                    table_body = "\n".join([
                        r"\begin{tabular}{cccc}",
                        r"\toprule",
                        rf"\textbf{{Frequency ({unit})}} & \textbf{{Re($S_{{11}}$)}} & "
                        rf"\textbf{{Im($S_{{11}}$)}} & \textbf{{$|S_{{11}}|$ (dB)}} \\",
                        r"\midrule",
                    ] + rows_tex + [
                        r"\bottomrule",
                        r"\end{tabular}",
                    ])
                    doc.append(NoEscape(table_body))
                    any_added = True

            if not any_added:
                doc.append(NoEscape(r"\textit{No step measurements available.}"))

    # ------------------------------------------------------------------ #

    def _create_cover_page(self, doc, freqs, sample_name, wizard_window, current_dt):
        from pylatex.utils import NoEscape

        wiz = wizard_window
        cal = getattr(wiz, "perm_calibration", None)
        technique = getattr(wiz, "selected_method", "") or "—"
        temp = getattr(wiz, "temperature_c", None)

        refs_text = "—"
        try:
            if cal is not None and getattr(cal, "ref1_key", None) and getattr(cal, "ref2_key", None):
                from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
                    get_reference_liquid,
                )
                refs_text = (
                    f"{get_reference_liquid(cal.ref1_key).display_name} / "
                    f"{get_reference_liquid(cal.ref2_key).display_name}"
                )
        except Exception:
            pass

        if freqs is not None and len(freqs) > 0:
            f0, f1 = float(freqs[0]), float(freqs[-1])
            div, unit = _freq_scale(np.asarray(freqs))
            freq_str = f"{f0/div:.3f}–{f1/div:.3f} {unit}"
            steps = getattr(wiz, "sweep_steps", None)
            if steps:
                freq_str += f", {steps} pts"
        else:
            freq_str = "—"

        def _esc(s):
            return str(s).replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")

        doc.append(NoEscape(r"\begin{titlepage}"))
        doc.append(NoEscape(r"\begin{center}"))
        doc.append(NoEscape(r"\vspace*{2cm}"))
        doc.append(NoEscape(r"\Huge \textbf{Material Characterization Report} \\[1.2cm]"))
        doc.append(NoEscape(r"\LARGE NanoVNA UTN Toolkit \\[0.8cm]"))
        doc.append(NoEscape(r"\large " + _esc(current_dt)))
        doc.append(NoEscape(r"\vspace{3cm}"))
        doc.append(NoEscape(r"\begin{flushleft}"))
        doc.append(NoEscape(r"\Large \textbf{Measurement Details:} \\[0.5cm]"))
        doc.append(NoEscape(r"\normalsize"))
        doc.append(NoEscape(r"\begin{itemize}"))
        doc.append(NoEscape(rf"\item \textbf{{Sample:}} {_esc(sample_name or 'Unknown')}"))
        doc.append(NoEscape(rf"\item \textbf{{Technique:}} {_esc(technique)}"))
        temp_str = f"{temp:.1f} °C" if temp is not None else "—"
        doc.append(NoEscape(rf"\item \textbf{{Temperature:}} {_esc(temp_str)}"))
        doc.append(NoEscape(rf"\item \textbf{{Reference Liquids:}} {_esc(refs_text)}"))
        doc.append(NoEscape(rf"\item \textbf{{Frequency Range:}} {_esc(freq_str)}"))

        # Data sources per standard
        if cal is not None:
            _LABELS = {"open": "Open", "short": "Short", "ref1": "Ref 1", "ref2": "Ref 2", "dut": "DUT"}
            src_parts = []
            for key, label in _LABELS.items():
                src = cal.get_source(key)
                if src is not None:
                    src_parts.append(f"{label}: {src}")
            if src_parts:
                doc.append(NoEscape(
                    rf"\item \textbf{{Data sources:}} {_esc(', '.join(src_parts))}"
                ))

        doc.append(NoEscape(r"\end{itemize}"))
        doc.append(NoEscape(r"\end{flushleft}"))
        doc.append(NoEscape(r"\end{center}"))
        doc.append(NoEscape(r"\end{titlepage}"))
