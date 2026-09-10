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

def _html_to_latex(html: str) -> str:
    """Convert QTextEdit HTML rich text to LaTeX markup."""
    import re
    from html.parser import HTMLParser

    if not html.strip().startswith("<"):
        # Plain text fallback — just escape special chars
        for ch, repl in [("\\", r"\textbackslash{}"), ("{", r"\{"), ("}", r"\}"),
                          ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                          ("#", r"\#"), ("_", r"\_")]:
            html = html.replace(ch, repl)
        return html

    def _escape(text):
        for ch, repl in [("\\", r"\textbackslash{}"), ("{", r"\{"), ("}", r"\}"),
                          ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                          ("#", r"\#"), ("_", r"\_"),
                          ("^", r"\textasciicircum{}"), ("~", r"\textasciitilde{}")]:
            text = text.replace(ch, repl)
        return text

    def _pt_size(pt):
        if pt <= 7:  return r"\tiny"
        if pt <= 8:  return r"\scriptsize"
        if pt <= 9:  return r"\footnotesize"
        if pt <= 10: return r"\small"
        if pt <= 12: return r"\normalsize"
        if pt <= 14: return r"\large"
        if pt <= 17: return r"\Large"
        if pt <= 20: return r"\LARGE"
        if pt <= 25: return r"\huge"
        return r"\Huge"

    class _Conv(HTMLParser):
        def __init__(self):
            super().__init__()
            self._buf = []
            self._stack = []   # [(tag, closer_str)]
            self._in_body = False
            self._skip = 0
            self._heading_pending = False
            self._p_buf_pos = 0      # buf position right after the last <p> newline
            self._pending_sec = None # pending section command waiting for title text

        def handle_starttag(self, tag, attrs):
            tag = tag.lower()
            if tag in ("head", "style", "meta", "title"):
                self._skip += 1
                return
            if self._skip:
                return
            if tag == "body":
                self._in_body = True
                return
            if not self._in_body:
                return
            attrs = dict(attrs)
            style = attrs.get("style", "")
            op, cl = "", ""
            bold = (tag in ("b", "strong") or
                    bool(re.search(r"font-weight\s*:\s*(bold|[6-9]\d\d)", style)))
            italic = (tag in ("i", "em") or
                      bool(re.search(r"font-style\s*:\s*italic", style)))
            underline = (tag == "u" or
                         bool(re.search(r"text-decoration[^;]*underline", style)))
            if bold:
                op += r"\textbf{"; cl = "}" + cl
            if italic:
                op += r"\textit{"; cl = "}" + cl
            if underline:
                op += r"\underline{"; cl = "}" + cl
            m = re.search(r"font-size\s*:\s*([\d.]+)pt", style)
            if m:
                cmd = _pt_size(float(m.group(1)))
                op += "{" + cmd + " "; cl = "}" + cl
            if tag == "br":
                self._buf.append("\\\\\n")
                return
            if tag in ("p", "div"):
                if self._buf and not self._buf[-1].endswith("\n\n"):
                    self._buf.append("\n\n")
                self._stack.append((tag, ""))
                self._p_buf_pos = len(self._buf)
                return
            if tag == "ul":
                self._buf.append("\n\\begin{itemize}\n")
                self._stack.append((tag, "\n\\end{itemize}\n"))
                return
            if tag == "ol":
                self._buf.append("\n\\begin{enumerate}\n")
                self._stack.append((tag, "\n\\end{enumerate}\n"))
                return
            if tag == "li":
                self._buf.append("\\item ")
                self._stack.append((tag, "\n"))
                return
            if op:
                self._buf.append(op)
            self._stack.append((tag, cl))

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag in ("head", "style", "meta", "title"):
                self._skip = max(0, self._skip - 1)
                return
            if self._skip or not self._in_body:
                return
            if tag == "body":
                self._in_body = False
                return
            if self._stack and self._stack[-1][0] == tag:
                _, cl = self._stack.pop()
                if cl:
                    self._buf.append(cl)
            if tag in ("p", "div"):
                if self._pending_sec is not None:
                    self._buf.append('}\n')   # close empty section title
                    self._pending_sec = None
                self._buf.append("\n\n")

        def handle_data(self, data):
            if not (self._in_body and not self._skip):
                return
            stripped = data.lstrip()
            # If a section command is waiting for its title text (split across data calls)
            if self._pending_sec is not None:
                content = _escape_unicode(_escape(stripped))
                if not content:
                    return  # keep waiting; handle_endtag will close if no content arrives
                self._buf.append(content + '}\n')
                self._pending_sec = None
                return
            # Detect markdown # / ## / ### heading prefixes.
            # (prefix, size_cmd_or_None, vspace_before, vspace_after)
            # size_cmd=None → LaTeX sectioning command; otherwise bold text with vspace
            _heading_map = [
                ('###', None,       '', ''),
                ('##',  None,       '', ''),
                ('#',   r'\LARGE', '1.2em', '0.3em'),
            ]
            for prefix, size_cmd, vspace_before, vspace_after in _heading_map:
                if stripped.startswith(prefix) and (
                    len(stripped) == len(prefix) or not stripped[len(prefix)].isalpha()
                ):
                    content = _escape_unicode(_escape(stripped[len(prefix):].lstrip()))
                    self._buf = self._buf[:self._p_buf_pos]
                    self._stack = [(t, c) for t, c in self._stack
                                   if t in ('p', 'div', 'ul', 'ol', 'li')]
                    if size_cmd is None:
                        sec_cmd = r'\subsubsection' if prefix == '###' else r'\subsection'
                        self._buf.append('\n' + sec_cmd + '{')
                        if content:
                            self._buf.append(content + '}\n')
                        else:
                            # Title will arrive in the next handle_data call
                            self._pending_sec = sec_cmd
                    else:
                        self._buf.append(
                            '\n' + r'\vspace{' + vspace_before + r'}' + '\n' +
                            r'{' + size_cmd + r'\textbf{\strut ' + content + '}}' + '\n' +
                            r'\vspace{' + vspace_after + r'}' + '\n'
                        )
                    self._heading_pending = True
                    return
            self._buf.append(_escape_unicode(_escape(data)))

        def result(self):
            text = "".join(self._buf)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()

    # Map Unicode chars that pdflatex can't handle to LaTeX equivalents
    _GREEK = {
        'α': r'$\alpha$', 'β': r'$\beta$', 'γ': r'$\gamma$',
        'δ': r'$\delta$', 'ε': r'$\varepsilon$', 'ζ': r'$\zeta$',
        'η': r'$\eta$', 'θ': r'$\theta$', 'λ': r'$\lambda$',
        'μ': r'$\mu$', 'π': r'$\pi$', 'σ': r'$\sigma$',
        'τ': r'$\tau$', 'φ': r'$\phi$', 'ω': r'$\omega$',
        'Γ': r'$\Gamma$', 'Δ': r'$\Delta$', 'Θ': r'$\Theta$',
        'Λ': r'$\Lambda$', 'Σ': r'$\Sigma$', 'Φ': r'$\Phi$',
        'Ω': r'$\Omega$',
        '°': r'$^{\circ}$', '±': r'$\pm$', '×': r'$\times$',
        '→': r'$\rightarrow$', '←': r'$\leftarrow$',
        '≈': r'$\approx$', '≤': r'$\leq$', '≥': r'$\geq$',
    }

    def _escape_unicode(text):
        # Map chars unsupported by pdflatex+inputenc[utf8] (Greek, math symbols)
        # Latin accented chars (é, ó, ñ, ü…) pass through — inputenc handles them
        for ch, repl in _GREEK.items():
            text = text.replace(ch, repl)
        return text

    c = _Conv()
    c.feed(html)
    return c.result()


# --------------------------------------------------------------------------- #

def _document_to_latex(qt_document) -> str:
    """Convert a QTextDocument to LaTeX by reading blocks directly.
    Handles ## / ### heading prefixes and inline bold/italic/underline."""
    from PySide6.QtGui import QFont

    _GREEK_MAP = {
        'α': r'$\alpha$', 'β': r'$\beta$', 'γ': r'$\gamma$',
        'δ': r'$\delta$', 'ε': r'$\varepsilon$', 'ζ': r'$\zeta$',
        'η': r'$\eta$', 'θ': r'$\theta$', 'λ': r'$\lambda$',
        'μ': r'$\mu$', 'π': r'$\pi$', 'σ': r'$\sigma$',
        'τ': r'$\tau$', 'φ': r'$\phi$', 'ω': r'$\omega$',
        'Γ': r'$\Gamma$', 'Δ': r'$\Delta$', 'Θ': r'$\Theta$',
        'Λ': r'$\Lambda$', 'Σ': r'$\Sigma$', 'Φ': r'$\Phi$',
        'Ω': r'$\Omega$',
        '°': r'$^{\circ}$', '±': r'$\pm$', '×': r'$\times$',
        '→': r'$\rightarrow$', '←': r'$\leftarrow$',
        '≈': r'$\approx$', '≤': r'$\leq$', '≥': r'$\geq$',
    }

    def _esc(text):
        for ch, repl in [("\\", r"\textbackslash{}"), ("{", r"\{"), ("}", r"\}"),
                          ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                          ("#", r"\#"), ("_", r"\_"),
                          ("^", r"\textasciicircum{}"), ("~", r"\textasciitilde{}")]:
            text = text.replace(ch, repl)
        for ch, repl in _GREEK_MAP.items():
            text = text.replace(ch, repl)
        return text

    from PySide6.QtGui import QTextListFormat

    _DEFAULT_PT = 10  # matches document().defaultFont() set in the dialog

    def _fragments(block):
        line = []
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            t = _esc(frag.text())
            fmt = frag.charFormat()
            if fmt.fontUnderline():
                t = f'\\underline{{{t}}}'
            if fmt.fontItalic():
                t = f'\\textit{{{t}}}'
            if fmt.fontWeight() >= 600:
                t = f'\\textbf{{{t}}}'
            pt = fmt.fontPointSize()
            if pt > 0 and abs(pt - _DEFAULT_PT) > 0.5:
                baseline = pt * 1.2
                t = f'{{\\fontsize{{{pt:.0f}pt}}{{{baseline:.1f}pt}}\\selectfont {t}}}'
            line.append(t)
            it += 1
        return ''.join(line)

    _BULLET_STYLES = {
        QTextListFormat.Style.ListDisc,
        QTextListFormat.Style.ListCircle,
        QTextListFormat.Style.ListSquare,
    }

    parts = []
    current_list = None          # QTextList object currently open
    current_env = None           # "itemize" or "enumerate"

    block = qt_document.begin()
    while block.isValid():
        tlist = block.textList()

        if tlist is not None:
            # --- list item ---
            if tlist is not current_list:
                # close previous list if any
                if current_list is not None:
                    parts.append(f'\\end{{{current_env}}}\n')
                fmt = tlist.format()
                if fmt.style() in _BULLET_STYLES:
                    current_env = "itemize"
                else:
                    current_env = "enumerate"
                parts.append(f'\\begin{{{current_env}}}\n')
                current_list = tlist
            parts.append(f'  \\item {_fragments(block)}\n')
        else:
            # close any open list
            if current_list is not None:
                parts.append(f'\\end{{{current_env}}}\n\n')
                current_list = None
                current_env = None

            text = block.text()
            if not text.strip():
                parts.append('\n')
            elif text.startswith("### "):
                parts.append(f'\\subsubsection{{{_esc(text[4:].strip())}}}\n')
            elif text.startswith("## "):
                parts.append(f'\\subsection{{{_esc(text[3:].strip())}}}\n')
            else:
                content = _fragments(block)
                if content.strip():
                    parts.append(content + '\n\n')
                else:
                    parts.append('\n')

        block = block.next()

    if current_list is not None:
        parts.append(f'\\end{{{current_env}}}\n')

    return ''.join(parts).strip()


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
        wizard_window, output_path, compiler_path, include_steps=False, notes="",
        s11_data=None, notes_doc=None, include_tables=False,
    ):
        """Build the .tex from already-rendered images and run LaTeX.

        Blocking and Qt-free, so it can be handed to a worker thread. Raises on
        failure instead of showing a dialog.
        """
        self._create_latex_document(
            freqs=freqs,
            eps_selected=eps_selected,
            s11_data=s11_data,
            image_files=image_files,
            file_path=Path(output_path).with_suffix(""),
            sample_name=sample_name,
            wizard_window=wizard_window,
            compiler_path=compiler_path,
            include_steps=include_steps,
            include_tables=include_tables,
            notes=notes,
            notes_doc=notes_doc,
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
        keys = ["permittivity", "smith"]
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

        _COLORS = {
            "open":  "#e67e22",
            "short": "#2980b9",
            "ref1":  "#27ae60",
            "ref2":  "#8e44ad",
            "dut":   "#c0392b",
        }

        image_files = {}
        for key, label in _LABELS.items():
            data = cal.get_measurement(key)
            if data is None:
                continue
            freqs_s, s11_s = np.asarray(data[0], dtype=float), np.asarray(data[1], dtype=complex)
            div, unit = _freq_scale(freqs_s)
            mag_db = 20 * np.log10(np.abs(s11_s) + 1e-15)
            color = _COLORS.get(key, "#1a6bbf")

            fig, ax = plt.subplots(figsize=(8, 4))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            ax.plot(freqs_s / div, mag_db, color=color, linewidth=1.8)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=11)
            ax.set_ylabel(r"$|S_{11}|$ (dB)", fontsize=11)
            ax.set_title(f"{label} — $|S_{{11}}|$", fontsize=12, pad=10)
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.16)
            path = os.path.join(output_dir, f"step_{key}.png")
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            image_files[f"step_{key}"] = path
        return image_files

    # ------------------------------------------------------------------ #

    def _create_latex_document(
        self, freqs, eps_selected, image_files, file_path,
        sample_name, wizard_window, compiler_path, include_steps=False, notes="",
        s11_data=None, notes_doc=None, include_tables=False,
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
        doc.preamble.append(Command("usepackage", "inputenc", options="utf8"))
        doc.preamble.append(Command("usepackage", "graphicx"))
        doc.preamble.append(Command("usepackage", "float"))
        doc.preamble.append(Command("usepackage", "textcomp"))
        doc.preamble.append(Command("usepackage", "longtable"))
        doc.preamble.append(Command("usepackage", "booktabs"))
        doc.preamble.append(Command("usepackage", "array"))
        doc.preamble.append(NoEscape(
            r"\usepackage[colorlinks=true,linkcolor=black,urlcolor=blue,"
            r"bookmarks=true,bookmarksopen=true]{hyperref}"
        ))

        current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._create_cover_page(doc, freqs, sample_name, wizard_window, current_dt)

        doc.append(NewPage())
        doc.append(NoEscape(r"\tableofcontents"))
        doc.append(NewPage())

        has_notes = notes_doc is not None or (notes and notes.strip())
        if has_notes:
            if notes_doc is not None:
                latex_notes = _document_to_latex(notes_doc)
            else:
                latex_notes = _html_to_latex(notes)
            if latex_notes.strip():
                doc.append(NewPage())
                with doc.create(Section("Notes")):
                    doc.append(NoEscape(
                        r"\setlength{\parindent}{0pt}"
                        r"\setlength{\parskip}{0.9em}"
                    ))
                    doc.append(NoEscape(latex_notes))

        doc.append(NewPage())
        with doc.create(Section("Measurement Results")):

            # --- Page: Permittivity graph + table ---
            if "permittivity" in image_files:
                with doc.create(Subsection(NoEscape(
                    r"Complex Permittivity $\varepsilon_r(f)$"
                ))):
                    with doc.create(Figure(position="H")) as fig_latex:
                        fig_latex.add_image(
                            image_files["permittivity"].replace("\\", "/"),
                            width=NoEscape(r"0.78\linewidth"),
                        )
                if include_tables and freqs is not None and eps_selected is not None:
                    doc.append(NoEscape(r"\vspace{1.2em}"))
                    self._build_permittivity_mini_table(doc, freqs, eps_selected, NoEscape)

            # --- Page: Smith S11 graph + table ---
            if "smith" in image_files:
                doc.append(NewPage())
                with doc.create(Subsection(NoEscape(r"$S_{11}$ \textemdash{} Smith Chart"))):
                    with doc.create(Figure(position="H")) as fig_latex:
                        fig_latex.add_image(
                            image_files["smith"].replace("\\", "/"),
                            width=NoEscape(r"0.55\linewidth"),
                        )
                if include_tables and freqs is not None and s11_data is not None:
                    doc.append(NoEscape(r"\vspace{1.2em}"))
                    self._build_s11_mini_table(doc, freqs, s11_data, NoEscape)

        # Calibration standard measurements (optional)
        if include_steps:
            self._build_step_sections(doc, image_files, wizard_window, NoEscape, NewPage,
                                      Section, Subsection, Figure)

        # Compile — two passes so lastpage / cross-references resolve correctly
        compiler_name = os.path.basename(compiler_path).replace(".exe", "")
        original_path = os.environ.get("PATH", "")
        compiler_dir = os.path.dirname(compiler_path)
        if compiler_dir:
            os.environ["PATH"] = compiler_dir + os.pathsep + original_path
        try:
            import logging
            _log = logging.getLogger(__name__)
            tex_dir = str(file_path.parent)
            tex_path = file_path.with_suffix(".tex")

            # First pass: let pylatex generate .tex and run pdflatex once
            # (it may exit 1 due to lastpage/cross-ref warnings — ignore)
            try:
                doc.generate_pdf(str(file_path), compiler=compiler_name, clean_tex=False)
            except Exception:
                pass

            # Second pass: resolve cross-references and lastpage
            cmd = [compiler_name, "--interaction=nonstopmode", str(tex_path)]
            result = subprocess.run(cmd, cwd=tex_dir, check=False, capture_output=True)
            if result.returncode != 0:
                output = result.stdout.decode("utf-8", errors="replace")
                error_lines = [l for l in output.splitlines()
                               if l.startswith("!") or l.startswith("l.")]
                _log.error("[PDF] pdflatex errors:\n%s", "\n".join(error_lines) or output[-2000:])
                raise subprocess.CalledProcessError(result.returncode, cmd)
        finally:
            os.environ["PATH"] = original_path

    # ------------------------------------------------------------------ #

    def _build_permittivity_mini_table(self, doc, freqs, eps_selected, NoEscape):
        """Permittivity table with all measurement points appended below the graph."""
        f_hz = np.asarray(freqs, dtype=float)
        eps  = np.asarray(eps_selected, dtype=complex)
        n    = len(f_hz)

        div, unit = (1e9, "GHz") if f_hz[-1] >= 0.5e9 else (1e6, "MHz") if f_hz[-1] >= 0.5e6 else (1e3, "kHz")

        rows_tex = []
        for i in range(n):
            f_val  = f_hz[i] / div
            re_val = float(np.real(eps[i]))
            im_val = float(np.imag(eps[i]))
            tan_d  = abs(im_val / re_val) if abs(re_val) > 1e-15 else 0.0
            rows_tex.append(
                rf"{f_val:.3f} & {re_val:.4f} & {im_val:+.4f} & {tan_d:.4f} \\"
            )

        table_body = "\n".join([
            r"\begin{longtable}{>{\centering\arraybackslash}p{3.0cm}"
            r">{\centering\arraybackslash}p{2.6cm}"
            r">{\centering\arraybackslash}p{2.6cm}"
            r">{\centering\arraybackslash}p{2.6cm}}",
            r"\toprule",
            rf"\textbf{{Frequency ({unit})}} & \textbf{{$\varepsilon_r'$}} & \textbf{{$\varepsilon_r''$}} & \textbf{{$\tan\delta$}} \\",
            r"\midrule",
            r"\endhead",
            r"\midrule",
            r"\multicolumn{4}{r}{\footnotesize\itshape (continued on next page)} \\",
            r"\endfoot",
            r"\bottomrule",
            r"\endlastfoot",
        ] + rows_tex + [
            r"\end{longtable}",
        ])
        doc.append(NoEscape(table_body))

    def _build_s11_mini_table(self, doc, freqs, s11_data, NoEscape):
        """S11 table with all measurement points appended below the Smith chart."""
        f_hz = np.asarray(freqs, dtype=float)
        s11  = np.asarray(s11_data, dtype=complex)
        n    = len(f_hz)

        div, unit = (1e9, "GHz") if f_hz[-1] >= 0.5e9 else (1e6, "MHz") if f_hz[-1] >= 0.5e6 else (1e3, "kHz")

        rows_tex = []
        for i in range(n):
            f_val  = f_hz[i] / div
            re_val = float(np.real(s11[i]))
            im_val = float(np.imag(s11[i]))
            db_val = 20 * np.log10(abs(complex(re_val, im_val)) + 1e-15)
            rows_tex.append(
                rf"{f_val:.3f} & {re_val:.4f} & {im_val:+.4f} & {db_val:.2f} \\"
            )

        table_body = "\n".join([
            r"\begin{longtable}{>{\centering\arraybackslash}p{3.0cm}"
            r">{\centering\arraybackslash}p{2.6cm}"
            r">{\centering\arraybackslash}p{2.6cm}"
            r">{\centering\arraybackslash}p{2.6cm}}",
            r"\toprule",
            rf"\textbf{{Frequency ({unit})}} & \textbf{{Re($S_{{11}}$)}} & \textbf{{Im($S_{{11}}$)}} & \textbf{{$|S_{{11}}|$ (dB)}} \\",
            r"\midrule",
            r"\endhead",
            r"\midrule",
            r"\multicolumn{4}{r}{\footnotesize\itshape (continued on next page)} \\",
            r"\endfoot",
            r"\bottomrule",
            r"\endlastfoot",
        ] + rows_tex + [
            r"\end{longtable}",
        ])
        doc.append(NoEscape(table_body))

    def _build_data_table(self, doc, freqs, eps_selected):
        """Append a longtable with Frequency / ε′ / ε″ / tan δ columns."""
        from pylatex.utils import NoEscape

        f_hz = np.asarray(freqs, dtype=float)
        eps  = np.asarray(eps_selected, dtype=complex)
        n    = len(f_hz)

        def _fv(v, decimals):
            return r"\textemdash{}" if not np.isfinite(v) else f"{v:.{decimals}f}"

        rows_latex = []
        for i in range(n):
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
        note = f"All {n_shown} measurement points."

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

        # Collect available steps first so we know whether to add the parent section
        available = []
        for key in _KEYS:
            img_key = f"step_{key}"
            if img_key not in image_files or cal is None:
                continue
            data = cal.get_measurement(key)
            if data is None:
                continue
            available.append((key, img_key, data))

        doc.append(NewPage())
        with doc.create(Section("Calibration Standard Measurements")):
            if not available:
                doc.append(NoEscape(r"\textit{No step measurements available.}"))
            else:
                for key, img_key, data in available:
                    label = _LABELS.get(key, key.capitalize())
                    freqs_s = np.asarray(data[0], dtype=float)
                    s11_s   = np.asarray(data[1], dtype=complex)
                    div, unit = _freq_scale(freqs_s)
                    n = len(freqs_s)

                    with doc.create(Subsection(label)):
                        with doc.create(Figure(position="H")) as fig_latex:
                            fig_latex.add_image(
                                image_files[img_key].replace("\\", "/"),
                                width=NoEscape(r"0.88\linewidth"),
                            )

                        doc.append(NoEscape(r"\vspace{1.2em}"))
                        rows_tex = []
                        for i in range(n):
                            f_val  = freqs_s[i] / div
                            re_val = float(np.real(s11_s[i]))
                            im_val = float(np.imag(s11_s[i]))
                            db_val = 20 * np.log10(abs(complex(re_val, im_val)) + 1e-15)
                            rows_tex.append(
                                f"{f_val:.3f} & {re_val:.4f} & {im_val:+.4f} & {db_val:.2f} \\\\"
                            )

                        table_body = "\n".join([
                            r"\begin{longtable}{>{\centering\arraybackslash}p{3.0cm}"
                            r">{\centering\arraybackslash}p{2.6cm}"
                            r">{\centering\arraybackslash}p{2.6cm}"
                            r">{\centering\arraybackslash}p{2.6cm}}",
                            r"\toprule",
                            rf"\textbf{{Frequency ({unit})}} & \textbf{{Re($S_{{11}}$)}} & "
                            rf"\textbf{{Im($S_{{11}}$)}} & \textbf{{$|S_{{11}}|$ (dB)}} \\",
                            r"\midrule",
                            r"\endhead",
                            r"\midrule",
                            r"\multicolumn{4}{r}{\footnotesize\itshape (continued on next page)} \\",
                            r"\endfoot",
                            r"\bottomrule",
                            r"\endlastfoot",
                        ] + rows_tex + [
                            r"\end{longtable}",
                        ])
                        doc.append(NoEscape(table_body))

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

        # Data sources per standard — one sub-item per source
        if cal is not None:
            _LABELS = {"open": "Open", "short": "Short", "ref1": "Ref 1", "ref2": "Ref 2", "dut": "DUT"}
            src_parts = []
            for key, label in _LABELS.items():
                src = cal.get_source(key)
                if src is not None:
                    src_parts.append((label, src))
            if src_parts:
                doc.append(NoEscape(r"\item \textbf{Data sources:}"))
                doc.append(NoEscape(r"\begin{itemize}"))
                for label, src in src_parts:
                    doc.append(NoEscape(rf"\item \textbf{{{_esc(label)}:}} {_esc(src)}"))
                doc.append(NoEscape(r"\end{itemize}"))

        doc.append(NoEscape(r"\end{itemize}"))
        doc.append(NoEscape(r"\end{flushleft}"))
        doc.append(NoEscape(r"\end{center}"))
        doc.append(NoEscape(r"\end{titlepage}"))
