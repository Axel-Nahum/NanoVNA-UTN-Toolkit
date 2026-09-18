# Material Characterization Module

UTN FRBA 2026 — Proyecto Final — Course R6051

**Authors:**
- Axel Nathanel Nahum ([@Axel-Nahum](https://github.com/Axel-Nahum))
- Fernando Castro Canosa ([@fcascan](https://github.com/fcascan)) (ME2)

---

## Overview

The Material Characterization module measures the complex permittivity **εr(f) = ε′(f) − jε″(f)** of liquid samples using an open-ended coaxial probe connected to the NanoVNA. It uses a two-reference liquid calibration to correct for probe geometry and cable effects, then solves for the unknown liquid's permittivity across the measured frequency range.

---

## How to Launch

From the main module selector window, choose **Material Characterization** and click **Start Wizard**.

---

## Main Window

The main measurement window shows:

- **Left panel**: S₁₁ Smith chart and magnitude chart for the current measurement
- **Right panel**: computed εr chart (ε′ real part and ε″ imaginary part vs frequency)
- **Bottom bar**: sweep controls and status
- **Sidebar**: step navigator and measurement summary

---

## Calibration Wizard

The characterization requires measuring five standards in a fixed order. The wizard walks through each step:

| Step | Standard | Purpose |
|------|----------|---------|
| 1 | **Open** | Probe in open air — open-circuit reference (Γ ≈ +1) |
| 2 | **Short** | Coplanar short on the probe face — short-circuit reference (Γ ≈ −1) |
| 3 | **Reference liquid 1** | First known liquid (e.g. distilled water) — calibration standard |
| 4 | **Reference liquid 2** | Second known liquid (e.g. IPA, ethanol) — calibration standard |
| 5 | **Unknown liquid** | Sample under test — permittivity is computed from this measurement |

### Per-step options

At each step the user can:

- **Measure** — sweep the NanoVNA and record the S₁₁ data
- **Re-measure** — discard the current result and sweep again
- **Import `.s1p`** — load a previously recorded S₁₁ file instead of measuring
- **Load preset** — use a stored measurement saved in a previous session

### OPEN pre-calibration (optional)

An optional pre-calibration step normalizes the liquid S₁₁ data to remove the effect of the cable and connector between the port and the probe. Enable it from the wizard configuration screen if the cable length is significant.

---

## Configuration Screen

Before starting the wizard, the configuration screen sets:

| Parameter | Description |
|-----------|-------------|
| Start frequency | Lower bound of the sweep range |
| Stop frequency | Upper bound of the sweep range |
| Number of points | Frequency resolution |
| Measurement temperature | Temperature in °C — used to look up reference liquid permittivity from tabulated data |
| Unknown liquid name | Label for the sample under test |
| Reference liquid 1 | Liquid used as the first calibration standard |
| Reference liquid 2 | Liquid used as the second calibration standard |

Reference liquid permittivity values are taken from tabulated data. If the selected temperature is outside the tabulated range for a liquid, a warning is shown and the value is extrapolated.

---

## Reference Liquids

The following reference liquids are available with tabulated εr(T, f) data:

- Distilled water
- Isopropyl alcohol (IPA)
- Ethanol
- Methanol
- Acetone
- Others (as defined in `calibration/reference_liquids/`)

The two chosen reference liquids must be different. Choosing the same liquid twice is flagged as an error and blocks the wizard from proceeding.

---

## Algorithm

After all five measurements are completed, the permittivity is computed per frequency point by solving a **5th-order polynomial** derived from the probe model:

1. The Open and Short measurements establish the probe's reflection endpoints
2. The two reference liquids anchor the mapping from measured Γ to εr
3. The unknown liquid's S₁₁ is mapped through this calibration to yield εr(f)
4. Branch selection ensures physical continuity of the result across frequency

---

## Result Screen

The result screen displays:

- **εr chart**: ε′ (real part) and ε″ (loss) vs frequency
- **Mean ε′** and **mean loss tangent** tan δ = ε″/ε′
- **Data source table**: shows whether each standard was measured, imported, or loaded from a preset
- **Intermediate data**: branch selection criterion and polynomial roots (expandable)

---

## Preset Management

Measurements of reference liquids can be saved as **presets** and reused in future sessions. This avoids re-measuring known liquids every time.

- Save a preset from the step screen after a successful measurement
- Presets are stored under `calibration/presets/` as `.s1p` files with metadata
- Presets can be deleted from the configuration screen using the trash button next to each reference row

---

## Edit Characterization

The **Edit Characterization** dialog lets you customize the εr chart appearance:

- Marker size and color for Marker 1 and Marker 2
- Line thickness and color for the ε′ and ε″ traces
- Y-axis limits

---

## PDF Export

Click **Export PDF** on the result screen to generate a LaTeX-compiled report. The report includes:

- Cover page with measurement metadata (date, temperature, sweep parameters, reference liquids)
- Smith S₁₁ chart and εr(f) chart
- Branch selection criterion
- Permittivity data table (ε′, ε″, tan δ per frequency point)
- Optional: per-standard S₁₁ chart and mini data table

---

## File Formats

| Format | Used for |
|--------|----------|
| `.s1p` (Touchstone 1-port) | Calibration standards (Open, Short, reference liquids, unknown) |
| `.ini` | Sweep configuration, temperature settings |
| `.json` | Preset metadata |
| `.pdf` | Exported characterization report |
