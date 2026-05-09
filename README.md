# NanoVNA-UTN-Toolkit

UTN FRBA 2026 - Proyecto Final - Course R6051

**Authors:**
- Axel Nathanel Nahum ([@Axel-Nahum](https://github.com/Axel-Nahum))
- Fernando Castro Canosa ([@fcascan](https://github.com/fcascan)) (ME2)

## PC Connection Steps
### 1. Install driver
- **Windows only**: 
  1. Install the driver found in "windows-driver": CypressDriverInstaller_1.exe
  2. Restart the computer

### 2. Configure baudrate on the nanoVNA
  1. Press the rocker button to open the menu, navigate to Config / CONNECTION
  2. In the first item, set CONNECTION to "USB"
  3. In the second item, set SERIAL SPEED to a convenient baudrate (e.g., 38400)

### 3. Configure baudrate in the operating system
- **Windows**: 
  1. Connect the nanoVNA to the PC without pressing any button
  2. Open Device Manager and look for the nanoVNA in the "Ports (COM & LPT)" section
  3. In Properties / Port Settings, select the corresponding baudrate in the "Bits per second" dropdown menu

## Steps to run the program
### 1. Install Python
- **Windows**: 
  1. Open the terminal (cmd).
  2. Run the command `python`. This will redirect to the Windows store to install the latest version of **Python Interpreter & Runtime**.

### 2. Update `pip`
Run the following command in the terminal to update `pip` to its latest version:
```bash
pip install --upgrade pip
```

### 3. Install dependencies
Install the necessary dependencies for the program:
```bash
pip install -r requirements.txt
```

**Alternative (manual installation):**
```bash
pip install PySide6 numpy scipy pyserial matplotlib qtawesome pylatex scikit-rf
```

### 4. Run the program
Execute the main program in a Python environment from the project root:
```bash
python main.py
```


## Steps to compile an executable version
### 1. Install PyInstaller
Install the PyInstaller package with the following command:
```bash
pip install pyinstaller
```

### 2. Build the executable
Run the following command to generate an executable file using the configuration file:
```bash
python -m PyInstaller NanoVNA-UTN-Toolkit.spec
```

**Alternative (direct command):**
```bash
python -m PyInstaller --onefile main.py --name "NanoVNA-UTN-Toolkit" --icon=icon.ico --hidden-import=PySide6 --hidden-import=NanoVNA_UTN_Toolkit --hidden-import=NanoVNA_UTN_Toolkit.compat --hidden-import=NanoVNA_UTN_Toolkit.Hardware --hidden-import=NanoVNA_UTN_Toolkit.Hardware.Hardware --hidden-import=NanoVNA_UTN_Toolkit.utils --paths=src
```

### 3. Run the compiled program
The generated executable will be in the dist/ directory. To run it:
```bash
dist/NanoVNA-UTN-Toolkit.exe
```

## Credits
This project was developed as part of the requirements for the **Electronic Measurements II** course at UTN FRBA during the 2025 academic year.
