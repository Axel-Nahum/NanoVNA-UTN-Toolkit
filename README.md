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
