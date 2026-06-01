"""
Smith Chart in real-time utilities for NanoVNA-UTN-Toolkit.
"""

import numpy as np
import logging

def initialize_realtime_smith(
    ax,
    trace_color="yellow",
    linewidth=2
):
    """
    Crea la línea que será reutilizada durante todo el sweep.
    """

    try:

        line, = ax.plot(
            [],
            [],
            color=trace_color,
            linewidth=linewidth,
            animated=False
        )

        start_marker, = ax.plot(
            [],
            [],
            marker='o',
            linestyle='None',
            markersize=6,
            color=trace_color
        )

        return line, start_marker

    except Exception as e:
        logging.error(
            f"[smith_chart_realtime.initialize_realtime_smith] {e}"
        )

        return None, None
    
def update_realtime_smith(
    line,
    start_marker,
    s_data
):
    """
    Actualiza una traza Smith existente.
    """

    try:

        if line is None:
            return

        if s_data is None:
            return

        if len(s_data) == 0:
            return

        x = np.real(s_data)
        y = np.imag(s_data)

        line.set_data(
            x,
            y
        )

        if start_marker is not None:

            start_marker.set_data(
                [x[0]],
                [y[0]]
            )

    except Exception as e:

        logging.error(
            f"[smith_chart_realtime.update_realtime_smith] {e}"
        )