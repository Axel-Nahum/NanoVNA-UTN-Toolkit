# Measurement Viewer — NanoVNA UTN Toolkit

The Measurement Viewer lets you load, compare, and inspect Touchstone measurement files (`.s1p`, `.s2p`) without running a live measurement. It is available from both the DUT Measurement and Material Characterization modules.

---

## Opening the Viewer

- From **DUT Measurement**: File → Measurement Viewer  
- From **Material Characterization**: File → Measurement Viewer  
- From the **main menu**: Measurement Viewer button

---

## Loading Files

Click **+ Add files** to select one or more `.s1p` or `.s2p` files, or **Add folder** to load all compatible files from a directory.

Loaded files appear in the left panel. The badge shows the total number of files loaded.

---

## View Modes

| Mode | Description |
|---|---|
| **Single** | Shows one file at a time. Click a file in the list to display it. |
| **Compare** | Overlays all selected files on the same chart for direct comparison. |

---

## Chart Layout

Select from the **Graphics** tab in the control panel:

- **2 charts**: one row — Magnitude on top, Phase (or Imaginary) below.
- **4 charts**: two columns — S11 and S21 side by side, each with its own Magnitude and Phase row.

**Parameter** (2-chart mode only):
- **S11** — reflection coefficient
- **S21** — transmission coefficient / permittivity (characterization mode)

**Display**:
- **Mag + Phase** — Magnitude [dB] and Phase [°]
- **Real + Imag** — Real and Imaginary parts

---

## Cursors

Enable up to two cursors from the **Cursors** tab.

- Click on a chart to place the active cursor.
- Drag horizontally to move it. The cursor snaps to the nearest data frequency (no interpolation).
- **Linked**: when enabled, both cursors move together across all charts.
- **Δ (C2 − C1)**: shows the frequency difference between cursor 2 and cursor 1.

Frequency units (kHz / MHz / GHz) are selected automatically based on the value.

---

## Y Range

From the **Range** tab:

- **Auto**: fits the Y axis to all visible data on each chart independently.
- **Grid**: toggles the grid on/off per chart.
- **Y min / Y max**: set manual limits. Leave both empty to restore auto.

---

## Export

From the **Export** tab, choose DPI and export mode:

| Option | Output |
|---|---|
| **Individual** | One PNG per chart (Mag [dB], Phase [°], Real, Imag). |
| **Pairs** | One PNG per pair (Mag + Phase, Real + Imag). |
| **4-chart** | All four charts in a single PNG. |

---

## Dark / Light Theme

Click the **Dark Mode 🌙 / Light Mode 🔆** button in the header to toggle the theme. The window reopens with the new theme applied.

The theme is shared with the rest of the application (controlled from **File → Preferences**).

---

## File Menu

| Item | Action |
|---|---|
| Clear Selection | Deselects all files in the list (charts reset). |
| Preferences… | Opens the application Preferences dialog. |
| ← Back | Returns to the module that opened the viewer. |

---

## Keyboard & Tips

- The file filter box accepts partial matches on filename.
- Files can be from different instruments or sessions; the viewer only reads the frequency and data columns.
- Export filenames are suggested based on the source file name and chart type.

---

## Version

2.4.0 — October 2026  
UTN FRBA — Proyecto Final
