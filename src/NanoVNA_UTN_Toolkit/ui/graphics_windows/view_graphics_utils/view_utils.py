import skrf as rf
import numpy as np
import os
import logging
import sys

import matplotlib.pyplot as plt

plt.rcParams['mathtext.fontset'] = 'cm'   # Fuente Computer Modern
plt.rcParams['text.usetex'] = False       # No requiere LaTeX externo
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'     # Coincide con el estilo de LaTeX
plt.rcParams['mathtext.rm'] = 'serif'     # Números y texto coherentes

# Suppress verbose matplotlib logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.lines import Line2D

# Suppress matplotlib debug logs

from pathlib import Path

from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTabWidget, QFrame, QSizePolicy, QApplication,
    QGroupBox, QRadioButton
)
from PySide6.QtCore import Qt, QSettings

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def create_tab1(self):

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/colors_config/config.ini",
        "ui/graphics_windows/ini/config.ini", 
        Path(__file__).resolve()
    )

    graph_type1 = settings.value("Tab1/GraphType1", "Magnitudes")
    s_param1 = settings.value("Tab1/SParameter", "S11")

    # Load configuration for UI colors and styles
    settings_dark_light = get_settings(
        "INI/dark_light_config/dark_light_config.ini",
        "ui/utils/settings/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )  

    groupbox_border = settings_dark_light.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
    groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}"

    # QFrame
    qframe_color = settings_dark_light.value("Dark_Light/QFrame/background-color", "white")

####################################################################################################
#--------- Tab1 -----------------------------------------------------------------------------------#
####################################################################################################

    # QLabel
    label_color = settings_dark_light.value("Dark_Light/QLabel/color", "white")

    tab1 = QWidget()
    tab1_layout = QHBoxLayout(tab1)
    tab1_layout.setContentsMargins(0, 0, 0, 0)
    tab1_layout.setSpacing(20)

    # --- Left panel ---
    left_panel = QWidget()
    left_layout = QVBoxLayout(left_panel)
    left_layout.setAlignment(Qt.AlignTop)
    left_layout.setSpacing(10)
    left_layout.setContentsMargins(0, 14, 0, 0)

    # --- Selector for S parameter ---
    graphic_param_selector = QGroupBox(" Select Parameter ")
    graphic_param_selector.setStyleSheet(groupbox_style)
    param_layout = QVBoxLayout()
    self.radio_s_tab1 = {}  
    for option in ["S11", "S21"]:
        rb = QRadioButton(option)
        rb.setStyleSheet(f"color: {label_color};")
        param_layout.addWidget(rb)
        self.radio_s_tab1[option] = rb  # 
    self.radio_s_tab1[s_param1].setChecked(True)
    graphic_param_selector.setLayout(param_layout)
    left_layout.addWidget(graphic_param_selector)

    # --- Selector for graph type ---
    graphic_type_selector = QGroupBox(" Selector Graphic 1 ")
    graphic_type_selector.setStyleSheet(groupbox_style)
    type_layout = QVBoxLayout()
    self.radio_buttons_tab1 = {} 
    for option in ["Smith Diagram", "Magnitude", "Phase"]:
        rb = QRadioButton(option)
        rb.setStyleSheet(f"color: {label_color};")
        type_layout.addWidget(rb)
        self.radio_buttons_tab1[option] = rb 
    self.radio_buttons_tab1[graph_type1].setChecked(True)
    graphic_type_selector.setLayout(type_layout)
    left_layout.addWidget(graphic_type_selector)

    # --- Figure and Canvas ---
    fig, ax = plt.subplots(figsize=(4,4))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.82, bottom=0.18)
    canvas = FigureCanvas(fig)
    canvas.setFixedSize(350, 350)

    tab1_layout.addWidget(left_panel, 1)
    tab1_layout.addWidget(canvas, 2)

    # --- Line below tab ---
    line_tab = QFrame()
    line_tab.setStyleSheet(f"""background-color: {qframe_color}; color: {qframe_color}""")
    line_tab.setFrameShape(QFrame.HLine)
    line_tab.setFrameShadow(QFrame.Plain)
    line_tab.setFixedHeight(2)

    tab1_container = QVBoxLayout()
    tab1_container.setContentsMargins(0, 0, 0, 0)
    tab1_container.setSpacing(0)
    tab1_container.addWidget(line_tab)
    tab1_container.addWidget(tab1)
    tab1_widget = QWidget()
    tab1_widget.setLayout(tab1_container)

    self.current_s_tab1 = s_param1
    self.current_graph_tab1 = graph_type1

    def update_graph():
        ax.clear()
        ax.legend().remove()

        self.current_s_tab1 = "S11" if self.radio_s_tab1["S11"].isChecked() else "S21"

        data = np.array([])
        #data = self.s11 if self.current_s_tab1 == "S11" else self.s21

        if self.radio_buttons_tab1["Smith Diagram"].isChecked():
            self.current_graph_tab1 = "Smith Diagram"
            ntw = rf.Network(frequency=self.freqs, s=data[:, np.newaxis, np.newaxis], z0=50)
            ntw.plot_s_smith(ax=ax, draw_labels=True, show_legend=False)
            ax.legend([Line2D([0],[0], color='blue')],[self.current_s_tab1], loc='upper left', bbox_to_anchor=(-0.17, 1.14))

            self.radio_s_tab1["S21"].setEnabled(False)
            self.radio_s_tab1["S11"].setChecked(True)

        elif self.radio_buttons_tab1["Magnitude"].isChecked():
            self.current_graph_tab1 = "Magnitude"

            self.radio_s_tab1["S21"].setEnabled(True)
            
            if np.any(data):
                ax.plot(self.freqs*1e-6, np.abs(data), color='blue', label=self.current_s_tab1)

            ax.set_xlabel(r"$\mathrm{Frequency\ [MHz]}$")
            ax.set_ylabel(r"$|%s|$" % self.current_s_tab1)

            ax.set_aspect('equal', 'box')    
            ax.grid(True)

            ax.spines['bottom'].set_color('grey')     
            ax.spines['bottom'].set_linewidth(0.7)

            ax.spines['left'].set_color('grey')      
            ax.spines['left'].set_linewidth(0.7)

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
        elif self.radio_buttons_tab1["Phase"].isChecked():
            self.current_graph_tab1 = "Phase"

            self.radio_s_tab1["S21"].setEnabled(True)

            if np.any(data):
                ax.plot(self.freqs*1e-6, np.angle(data, deg=True), color='blue', label=self.current_s_tab1)

            ax.set_xlabel(r"$\mathrm{Frequency\ [MHz]}$")
            ax.set_ylabel(r'$\phi_{%s}$ [°]' % self.current_s_tab1)

            ax.set_aspect('equal', 'box')    
            ax.grid(True)

            ax.spines['bottom'].set_color('grey')     
            ax.spines['bottom'].set_linewidth(0.7)

            ax.spines['left'].set_color('grey')      
            ax.spines['left'].set_linewidth(0.7)

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        canvas.draw()

    # --- Conectar radio buttons a update_graph ---
    for rb in self.radio_s_tab1.values():
        rb.toggled.connect(update_graph)
    for rb in self.radio_buttons_tab1.values():
        rb.toggled.connect(update_graph)

    # --- Inicializa el gráfico ---
    update_graph()

    return tab1_widget, fig, ax, canvas, left_panel, update_graph, self.current_s_tab1, self.current_graph_tab1

#------------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------------#

def create_tab2(self):

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/colors_config/config.ini",
        "ui/graphics_windows/ini/config.ini", 
        Path(__file__).resolve()
    )

    graph_type2 = settings.value("Tab2/GraphType2", "Smith Diagram")
    s_param2 = settings.value("Tab2/SParameter", "S11")

    # Load configuration for UI colors and styles
    settings_dark_light = get_settings(
        "INI/dark_light_config/dark_light_config.ini",
        "ui/utils/settings/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )  

    groupbox_border = settings_dark_light.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
    groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}"

    # QFrame
    qframe_color = settings_dark_light.value("Dark_Light/QFrame/background-color", "white")

    # QLabel
    label_color = settings_dark_light.value("Dark_Light/QLabel/color", "white")

####################################################################################################
#--------- Tab2 -----------------------------------------------------------------------------------#
####################################################################################################

    tab2 = QWidget()
    tab2_layout = QHBoxLayout(tab2)
    tab2_layout.setContentsMargins(0, 0, 0, 0)
    tab2_layout.setSpacing(20)

    # --- Right panel ---
    right_panel2 = QWidget()
    right_layout2 = QVBoxLayout(right_panel2)
    right_layout2.setAlignment(Qt.AlignTop)
    right_layout2.setSpacing(10)
    right_layout2.setContentsMargins(0, 14, 0, 0)

    # --- Selector for S parameter ---
    graphic_param_selector = QGroupBox(" Select Parameter ")
    graphic_param_selector.setStyleSheet(groupbox_style)
    param_layout = QVBoxLayout()
    self.radio_s_tab2 = {}
    for option in ["S11", "S21"]:
        rb = QRadioButton(option)
        param_layout.addWidget(rb)
        rb.setStyleSheet(f"color: {label_color};")
        self.radio_s_tab2[option] = rb
    self.radio_s_tab2[s_param2].setChecked(True)
    graphic_param_selector.setLayout(param_layout)
    right_layout2.addWidget(graphic_param_selector)

    # --- Selector for graph type ---
    graphic_type_selector = QGroupBox(" Selector Graphic 2 ")
    graphic_type_selector.setStyleSheet(groupbox_style)
    type_layout = QVBoxLayout()
    self.radio_buttons_tab2 = {}
    for option in ["Smith Diagram", "Magnitude", "Phase"]:
        rb = QRadioButton(option)
        type_layout.addWidget(rb)
        rb.setStyleSheet(f"color: {label_color};")
        self.radio_buttons_tab2[option] = rb
    self.radio_buttons_tab2[graph_type2].setChecked(True)
    graphic_type_selector.setLayout(type_layout)
    right_layout2.addWidget(graphic_type_selector)

    # --- Figure and Canvas ---
    fig, ax = plt.subplots(figsize=(4,4))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.82, bottom=0.18)
    canvas = FigureCanvas(fig)
    canvas.setFixedSize(350, 350)

    tab2_layout.addWidget(right_panel2, 1)
    tab2_layout.addWidget(canvas, 2)

    # --- Line below tab ---
    line_tab = QFrame()
    line_tab.setStyleSheet(f"""background-color: {qframe_color}; color: {qframe_color}""")
    line_tab.setFrameShape(QFrame.HLine)
    line_tab.setFrameShadow(QFrame.Plain)
    line_tab.setFixedHeight(2)

    tab2_container = QVBoxLayout()
    tab2_container.setContentsMargins(0, 0, 0, 0)
    tab2_container.setSpacing(0)
    tab2_container.addWidget(line_tab)
    tab2_container.addWidget(tab2)
    tab2_widget = QWidget()
    tab2_widget.setLayout(tab2_container)

    self.current_s_tab2 = "S11"
    self.current_graph_tab2 = "Magnitude"

    def update_graph():
        ax.clear()
        ax.legend().remove()

        self.current_s_tab2 = "S11" if self.radio_s_tab2["S11"].isChecked() else "S21"
        #data = self.s11 if self.current_s_tab2 == "S11" else self.s21

        data = np.array([])

        if self.radio_buttons_tab2["Smith Diagram"].isChecked():  
            self.current_graph_tab2 = "Smith Diagram"
            ntw = rf.Network(frequency=self.freqs, s=data[:, np.newaxis, np.newaxis], z0=50)
            ntw.plot_s_smith(ax=ax, draw_labels=True, show_legend=False)
            ax.legend([Line2D([0],[0], color='blue')],[self.current_s_tab2], loc='upper left', bbox_to_anchor=(-0.17, 1.14))

            self.radio_s_tab2["S21"].setEnabled(False)
            self.radio_s_tab2["S11"].setChecked(True)

        elif self.radio_buttons_tab2["Magnitude"].isChecked(): 
            self.current_graph_tab2 = "Magnitude"
            if np.any(data):
                ax.plot(self.freqs*1e-6, np.abs(data), color='blue', label=self.current_s_tab2)

            ax.set_xlabel(r"$\mathrm{Frequency\ [MHz]}$")
            ax.set_ylabel(r"$|%s|$" % self.current_s_tab2)

            ax.set_aspect('equal', 'box')  
            ax.grid(True)

            self.radio_s_tab2["S21"].setEnabled(True)

            ax.spines['bottom'].set_color('grey')     
            ax.spines['bottom'].set_linewidth(0.7)

            ax.spines['left'].set_color('grey')      
            ax.spines['left'].set_linewidth(0.7)

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        elif self.radio_buttons_tab2["Phase"].isChecked(): 
            self.current_graph_tab2 = "Phase"
            if np.any(data):
                ax.plot(self.freqs*1e-6, np.angle(data, deg=True), color='blue', label=self.current_s_tab2)

            ax.set_xlabel(r"$\mathrm{Frequency\ [MHz]}$")
            ax.set_ylabel(r'$\phi_{%s}$ [°]' % self.current_s_tab2)
            
            ax.set_aspect('equal', 'box')   
            ax.grid(True)

            self.radio_s_tab2["S21"].setEnabled(True)

            ax.spines['bottom'].set_color('grey')     
            ax.spines['bottom'].set_linewidth(0.7)

            ax.spines['left'].set_color('grey')      
            ax.spines['left'].set_linewidth(0.7)

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
        canvas.draw()

    for rb in self.radio_s_tab2.values(): 
        rb.toggled.connect(update_graph)
    for rb in self.radio_buttons_tab2.values():  
        rb.toggled.connect(update_graph)

    # --- Inicializa el gráfico ---
    update_graph()

    return tab2_widget, fig, ax, canvas, right_panel2, update_graph, self.current_s_tab2, self.current_graph_tab2

