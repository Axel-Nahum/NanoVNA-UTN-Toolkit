# NanoVNA-UTN-Toolkit

UTN FRBA 2026 — Proyecto Final — Course R6051

**Authors:**
- Axel Nathanel Nahum ([@Axel-Nahum](https://github.com/Axel-Nahum))
- Fernando Castro Canosa ([@fcascan](https://github.com/fcascan)) (ME2)

---

## PC Connection Steps

### 1. Install driver
- **Windows only**:
  1. Install the driver found in `windows-driver/`: `CypressDriverInstaller_1.exe`
  2. Restart the computer

### 2. Configure baudrate on the NanoVNA
  1. Press the rocker button to open the menu, navigate to **Config / CONNECTION**
  2. In the first item, set CONNECTION to `USB`
  3. In the second item, set SERIAL SPEED to a convenient baudrate (e.g. 38400)

### 3. Configure baudrate in the operating system
- **Windows**:
  1. Connect the NanoVNA to the PC without pressing any button
  2. Open Device Manager and locate the NanoVNA under **Ports (COM & LPT)**
  3. In **Properties / Port Settings**, select the matching baudrate in the **Bits per second** dropdown

---

## Steps to Run the Program

### 1. Install Python
- **Windows**:
  1. Open a terminal (`cmd`).
  2. Run `python` — Windows Store will open to install the latest **Python Interpreter & Runtime**.

### 2. Update `pip`
```bash
pip install --upgrade pip
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

**Alternative (manual):**
```bash
pip install PySide6 numpy scipy pyserial matplotlib qtawesome pylatex scikit-rf filterpy
```

### 4. Run the program
From the project root:
```bash
python main.py
```

---

## Steps to Compile an Executable

### 1. Install PyInstaller
```bash
pip install pyinstaller
```

### 2. Build the executable
```bash
python -m PyInstaller NanoVNA-UTN-Toolkit.spec
```

**Alternative (direct command):**
```bash
python -m PyInstaller --onefile main.py --name "NanoVNA-UTN-Toolkit" --icon=icon.ico --hidden-import=PySide6 --hidden-import=NanoVNA_UTN_Toolkit --hidden-import=NanoVNA_UTN_Toolkit.compat --hidden-import=NanoVNA_UTN_Toolkit.Hardware --hidden-import=NanoVNA_UTN_Toolkit.Hardware.Hardware --hidden-import=NanoVNA_UTN_Toolkit.utils --paths=src
```

### 3. Run the compiled program
The executable is generated in `dist/`:
```bash
dist/NanoVNA-UTN-Toolkit.exe
```

---

## DUT Measurement Mode

The toolkit includes a full-featured S-parameter measurement environment for characterizing a Device Under Test (DUT) using the NanoVNA.

### How to launch
From the main window, select **DUT Measurement** from the mode selector and click **Start**.

### Calibration
Before measuring, a calibration step corrects for systematic errors introduced by cables and connectors. Available methods:

| Method | Standards required | Corrects |
|--------|-------------------|---------|
| **OSM** (Open–Short–Match) | Open, Short, Match | S₁₁ reflection errors |
| **Thru Normalization** | Thru | S₂₁ transmission tracking |
| **Open/Short Normalization** | Open, Short | S₁₁ reflection (simplified) |
| **1-Port + N** | Open, Short, Match + Thru | S₁₁ + S₂₁ |
| **Enhanced-Response** | Open, Short, Match + Thru | Full 2-port (reflection + transmission) |
| **Kit-based** | Calibration kit `.s2p` | Full 2-port using a known cal kit |
| **No Calibration** | — | Raw uncalibrated data |
| **Import DUT** | `.s2p` file | Load previously measured DUT |

Each calibration method has its own guided wizard that walks through the required standards one by one.

### Sweep configuration
The sweep (start frequency, stop frequency, number of points) is configured from the **Sweep Options** panel. Settings persist between sessions.

### Measurement
Click **Run Sweep** to perform a single measurement. Results are displayed as:
- S₁₁ and S₂₁ magnitude (dB) vs frequency
- Phase vs frequency
- Smith chart (S₁₁)
- Polar chart (S₂₁)

### Real-time mode
Enable the **Single Sweep Mode** checkbox to toggle real-time continuous sweeping. While active, the sweep repeats automatically and the button switches to **Reset Kalman**. Disabling it returns to single-sweep mode.

### Signal filters
An optional **Kalman filter** can be applied to smooth noisy measurements. Presets (Light, Default, Strong) are available from the Plot menu. Set to **Off** to disable filtering.

### Export
Click **Export** to generate a PDF report with:
- Cover page with measurement metadata and calibration method
- S-parameter charts (magnitude, phase, Smith, polar)
- Marker readouts
- Optional: data table with S₁₁ and S₂₁ values per frequency point

### Markers
Two independent draggable markers are available per chart. Each shows the frequency and S-parameter value at the cursor position.

---

## Material Characterization Mode

The toolkit includes a guided wizard to characterize the complex permittivity **εr(f)** of liquid samples using an open-ended coaxial probe connected to the NanoVNA.

### How to launch
From the main window, select **Material Characterization** from the mode selector and click **Start Wizard**.

### Wizard overview
The wizard walks through the following steps in order:

| Step | Standard | Purpose |
|------|----------|---------|
| 1 | **Open** | Probe in open air — open-circuit reference (Γ ≈ +1) |
| 2 | **Short** | Coplanar short on probe face — short-circuit reference (Γ ≈ −1) |
| 3 | **Reference 1** | Known liquid (e.g. distilled water) — first calibration standard |
| 4 | **Reference 2** | Known liquid (e.g. IPA, ethanol) — second calibration standard |
| 5 | **Unknown liquid** | Sample under test — permittivity is computed from this |

Each step shows a live Smith chart and lets you re-measure, import a `.s1p` file, or load a saved preset.  
An optional **OPEN pre-calibration** normalises the liquid S₁₁ to correct cable/connector effects.

### Result screen
After all measurements are complete, the wizard computes **εr(f)** by solving a 5th-order polynomial per frequency and tracking a physically continuous branch. The result screen shows:
- εr chart (real part ε′ and loss ε″ vs frequency)
- Mean ε′ and mean loss tangent
- Data sources per standard (measured / imported / preset)
- Intermediate data and branch selection criterion

### PDF export
Click **Export PDF** on the result screen to generate a LaTeX-compiled report including:
- Cover page with measurement metadata
- Smith S₁₁ chart and εr(f) chart
- Branch selection criterion
- Permittivity data table
- Optional: S₁₁ chart + mini-table per calibration standard

---

## Credits
This project was developed as part of the **Proyecto Final** course at UTN FRBA during the 2026 academic year.
