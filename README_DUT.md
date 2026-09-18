# DUT Measurement Module

UTN FRBA 2026 — Proyecto Final — Course R6051

**Authors:**
- Axel Nathanel Nahum ([@Axel-Nahum](https://github.com/Axel-Nahum))
- Fernando Castro Canosa ([@fcascan](https://github.com/fcascan)) (ME2)

---

## Overview

The DUT Measurement module provides a full S-parameter measurement environment for characterizing a Device Under Test using the NanoVNA. It covers reflection (S₁₁) and transmission (S₂₁) measurements, several calibration methods, real-time sweeping, signal filtering, and PDF export.

---

## How to Launch

From the main module selector window, choose **DUT Measurement** and click **Start**.

---

## Main Window

The main graphics window is the central hub of the DUT module. It contains:

- **Left panel**: S₁₁ chart (magnitude in dB and phase) and Smith chart
- **Right panel**: S₂₁ chart (magnitude in dB and phase) and polar chart
- **Bottom bar**: sweep controls, real-time toggle, progress bar, reconnect button

### Sweep controls

| Control | Description |
|---------|-------------|
| **Run Sweep** | Performs a single measurement sweep |
| **Single Sweep Mode** checkbox | Unchecked = real-time continuous mode; checked = single sweep mode |
| **Reset Kalman** | Resets the Kalman filter state (shown instead of Run Sweep during real-time) |
| **Reconnect** | Re-establishes the serial connection to the NanoVNA |
| Progress bar | Shows sweep progress (0–100 %) |

### Initial auto-sweep

When the graphics window opens, a single sweep runs automatically to populate the charts. The **Single Sweep Mode** checkbox is disabled (grayed out) during this initial sweep and re-enables once the first sweep completes.

---

## Calibration

Before measuring a DUT, a calibration corrects for systematic errors introduced by cables, connectors, and probe losses. The calibration wizard is launched from the **Calibration** menu.

### Available methods

| Method | Standards required | What it corrects |
|--------|-------------------|-----------------|
| **OSM** (Open–Short–Match) | Open, Short, Match | S₁₁ directivity, source match, reflection tracking |
| **Thru Normalization** | Thru | S₂₁ transmission tracking |
| **Open/Short Normalization** | Open, Short | S₁₁ reflection (simplified 2-term) |
| **1-Port + N** | Open, Short, Match + Thru | S₁₁ (full OSM) + S₂₁ (thru normalization) |
| **Enhanced-Response** | Open, Short, Match + Thru | Full 2-port: reflection + transmission |
| **Kit-based** | Calibration kit `.s2p` file | Full 2-port using a known commercial calibration kit |
| **No Calibration** | — | Raw uncalibrated data (no correction applied) |
| **Import DUT** | `.s2p` file | Load a previously measured and exported DUT |

### Calibration wizard

Each method launches a step-by-step wizard:

1. Select the calibration method from the Calibration menu
2. Connect each standard (Open, Short, Match, Thru) as instructed
3. Click **Measure** for each standard — the wizard sweeps and stores the result
4. After all standards are measured, click **Apply Calibration**

Calibration results are stored in `.s2p` files under `calibration/` and persist between sessions.

---

## Sweep Configuration

The sweep parameters are configured from **Sweep Options** (accessible from the toolbar or menu).

| Parameter | Description |
|-----------|-------------|
| Start frequency | Lower bound of the sweep range |
| Stop frequency | Upper bound of the sweep range |
| Number of points | Resolution of the frequency sweep (segments) |
| Unit | Hz / kHz / MHz / GHz |

Settings persist between sessions via INI file.

---

## Real-Time Mode

Uncheck the **Single Sweep Mode** checkbox to enter real-time continuous sweeping. In this mode:

- The NanoVNA sweeps repeatedly without user intervention
- The charts update after each completed sweep
- The button label changes to **Reset Kalman** (to reset filter state without stopping the loop)
- Re-checking the checkbox stops real-time and returns to single-sweep mode

---

## Signal Filters

An optional **Kalman filter** smooths noisy measurements by tracking a state estimate across sweeps. Access it from **Plot → Signal Filters**.

| Preset | Effect |
|--------|--------|
| **Off** | No filtering — raw data displayed |
| **Light** | Minimal smoothing |
| **Default** | Balanced noise reduction |
| **Strong** | Heavy smoothing (slower to track rapid changes) |

- The filter state resets automatically on each new single sweep (when Single Sweep Mode is on)
- During real-time mode the filter runs continuously; use **Reset Kalman** to clear the state

---

## Charts

Four charts are displayed simultaneously:

| Chart | Signal | Display |
|-------|--------|---------|
| Top-left | S₁₁ | Magnitude (dB) and phase vs frequency |
| Bottom-left | Smith | S₁₁ plotted on a Smith chart |
| Top-right | S₂₁ | Magnitude (dB) and phase vs frequency |
| Bottom-right | Polar | S₂₁ plotted on a polar diagram |

### Markers

Each chart supports two independent draggable markers:

- **Marker 1** and **Marker 2** can be enabled/disabled independently per chart
- Dragging a marker updates its frequency readout and the corresponding S-parameter value in real time
- Marker positions reset to 0 Hz after each sweep

### Edit Graphics

The **Edit Graphics** dialog (accessible from the toolbar) lets you customize the chart appearance:

- Marker size and color for Marker 1 and Marker 2
- Line thickness and color for each trace
- Chart limits (frequency axis, Y axis)

---

## Export

Click **Export** to generate a PDF report. The report includes:

- Cover page with measurement date, calibration method, and sweep parameters
- All four S-parameter charts
- Marker readouts at the time of export
- Optional: frequency–S-parameter data table

---

## File Formats

| Format | Used for |
|--------|----------|
| `.s2p` (Touchstone) | Calibration standards, calibration kit files, DUT import/export |
| `.ini` | Sweep configuration, filter presets, calibration metadata |
| `.pdf` | Exported measurement report |
