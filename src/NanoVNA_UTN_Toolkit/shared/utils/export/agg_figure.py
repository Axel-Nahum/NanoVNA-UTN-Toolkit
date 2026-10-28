"""
Figures for report images: plain ``Figure`` on an Agg canvas, usable off the GUI thread.

EN: ``plt.subplots`` registers the figure with pyplot and, with the QtAgg backend,
creates a Qt canvas and a figure manager window. Done from a worker thread (the
PDF compile task renders calibration charts there) that creates Qt widgets off
the GUI thread; done from the GUI thread it leaks one hidden window per figure
unless ``plt.close`` follows. A bare ``Figure`` with ``FigureCanvasAgg`` has no
registry, no Qt, and ``savefig`` is pure Agg rasterization: safe in a worker.

ES: Figuras de reporte sin pyplot ni Qt: ``savefig`` es solo Agg, seguro en un
hilo de trabajo.
"""

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def new_agg_figure(figsize=None, **fig_kwargs):
    """``(fig, ax)`` like ``plt.subplots(figsize=...)`` but pyplot- and Qt-free."""
    fig = Figure(figsize=figsize, **fig_kwargs)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    return fig, ax
