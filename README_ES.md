# NanoVNA-UTN-Toolkit

UTN FRBA 2026 — Proyecto Final — Curso R6051

**Autores:**
- Axel Nathanel Nahum ([@Axel-Nahum](https://github.com/Axel-Nahum))
- Fernando Castro Canosa ([@fcascan](https://github.com/fcascan)) (ME2)

---

## Pasos para la conexión a la PC

### 1. Instalar driver
- **Solo para Windows**:
  1. Instalar el driver que se encuentra en `windows-driver/`: `CypressDriverInstaller_1.exe`
  2. Reiniciar el equipo

### 2. Configurar el baudrate en el NanoVNA
  1. Pulsar el botón rocker para desplegar el menú, navegar a **Config / CONNECTION**
  2. En el primer ítem configurar CONNECTION como `USB`
  3. En el segundo ítem configurar SERIAL SPEED a un baudrate de conveniencia (por ejemplo 38400)

### 3. Configurar el baudrate en el sistema operativo
- **Windows**:
  1. Conectar el NanoVNA a la PC sin pulsar ningún botón
  2. Abrir el Administrador de Dispositivos y buscar el NanoVNA en la sección **Puertos (COM y LPT)**
  3. En **Propiedades / Configuración del puerto**, seleccionar el baudrate correspondiente en el menú desplegable de **Bits por segundo**

---

## Pasos para ejecutar el programa

### 1. Instalar Python
- **Windows**:
  1. Abrir la terminal (`cmd`).
  2. Ejecutar `python` — la Tienda de Windows se abrirá para instalar la última versión del **Python Interpreter & Runtime**.

### 2. Actualizar `pip`
```bash
pip install --upgrade pip
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

**Alternativa (instalación manual):**
```bash
pip install PySide6 numpy scipy pyserial matplotlib qtawesome pylatex scikit-rf filterpy
```

### 4. Ejecutar el programa
Desde la raíz del proyecto:
```bash
python main.py
```

---

## Pasos para compilar una versión ejecutable

### 1. Instalar PyInstaller
```bash
pip install pyinstaller
```

### 2. Construir el ejecutable
```bash
python -m PyInstaller NanoVNA-UTN-Toolkit.spec
```

**Alternativa (comando directo):**
```bash
python -m PyInstaller --onefile main.py --name "NanoVNA-UTN-Toolkit" --icon=icon.ico --hidden-import=PySide6 --hidden-import=NanoVNA_UTN_Toolkit --hidden-import=NanoVNA_UTN_Toolkit.compat --hidden-import=NanoVNA_UTN_Toolkit.Hardware --hidden-import=NanoVNA_UTN_Toolkit.Hardware.Hardware --hidden-import=NanoVNA_UTN_Toolkit.utils --paths=src
```

### 3. Ejecutar el programa compilado
El ejecutable generado se encuentra en `dist/`:
```bash
dist/NanoVNA-UTN-Toolkit.exe
```

---

## Modo de Medición de DUT

El toolkit incluye un entorno completo de medición de parámetros S para caracterizar un Dispositivo Bajo Ensayo (DUT) usando el NanoVNA.

### Cómo iniciarlo
Desde la ventana principal, seleccionar **Medición de DUT** en el selector de modo y hacer clic en **Iniciar**.

### Calibración
Antes de medir, un paso de calibración corrige los errores sistemáticos introducidos por cables y conectores. Métodos disponibles:

| Método | Estándares requeridos | Corrige |
|--------|-----------------------|---------|
| **OSM** (Open–Short–Match) | Open, Short, Match | Errores de reflexión S₁₁ |
| **Thru Normalization** | Thru | Seguimiento de transmisión S₂₁ |
| **Open/Short Normalization** | Open, Short | Reflexión S₁₁ (simplificado) |
| **1-Port + N** | Open, Short, Match + Thru | S₁₁ + S₂₁ |
| **Enhanced-Response** | Open, Short, Match + Thru | 2 puertos completo (reflexión + transmisión) |
| **Kit-based** | Kit de calibración `.s2p` | 2 puertos completo usando kit conocido |
| **Sin Calibración** | — | Datos crudos sin calibrar |
| **Importar DUT** | Archivo `.s2p` | Cargar DUT medido previamente |

Cada método de calibración tiene su propio asistente guiado que recorre los estándares requeridos uno por uno.

### Configuración del barrido
El barrido (frecuencia de inicio, frecuencia de fin, número de puntos) se configura desde el panel **Opciones de Barrido**. La configuración persiste entre sesiones.

### Medición
Hacer clic en **Run Sweep** para realizar una medición única. Los resultados se muestran como:
- Magnitud de S₁₁ y S₂₁ (dB) en función de la frecuencia
- Fase en función de la frecuencia
- Carta de Smith (S₁₁)
- Diagrama polar (S₂₁)

### Modo tiempo real
Activar el checkbox **Single Sweep Mode** para alternar entre barrido continuo en tiempo real y barrido único. Mientras está activo, el barrido se repite automáticamente y el botón cambia a **Reset Kalman**. Al desactivarlo vuelve al modo de barrido único.

### Filtros de señal
Un **filtro de Kalman** opcional puede aplicarse para suavizar mediciones ruidosas. Los presets disponibles (Light, Default, Strong) se acceden desde el menú Plot. Seleccionar **Off** para deshabilitarlo.

### Exportación
Hacer clic en **Exportar** para generar un reporte PDF con:
- Carátula con metadatos de la medición y método de calibración
- Gráficos de parámetros S (magnitud, fase, Smith, polar)
- Lecturas de marcadores
- Opcional: tabla de datos con valores S₁₁ y S₂₁ por punto de frecuencia

### Marcadores
Dos marcadores independientes arrastrables disponibles por gráfico. Cada uno muestra la frecuencia y el valor del parámetro S en la posición del cursor.

---

## Modo de Caracterización de Materiales

El toolkit incluye un asistente guiado para caracterizar la permitividad compleja **εr(f)** de muestras líquidas usando una sonda coaxial de extremo abierto conectada al NanoVNA.

### Cómo iniciarlo
Desde la ventana principal, seleccionar **Caracterización de Materiales** en el selector de modo y hacer clic en **Iniciar asistente**.

### Resumen del asistente
El asistente recorre los siguientes pasos en orden:

| Paso | Patrón | Propósito |
|------|--------|-----------|
| 1 | **Open** | Sonda en el aire — referencia de circuito abierto (Γ ≈ +1) |
| 2 | **Short** | Cortocircuito coplanar en la cara de la sonda — referencia de circuito corto (Γ ≈ −1) |
| 3 | **Referencia 1** | Líquido conocido (p. ej. agua destilada) — primer patrón de calibración |
| 4 | **Referencia 2** | Líquido conocido (p. ej. IPA, etanol) — segundo patrón de calibración |
| 5 | **Líquido incógnita** | Muestra bajo ensayo — la permitividad se calcula a partir de esta medición |

Cada paso muestra una carta de Smith en vivo y permite volver a medir, importar un archivo `.s1p` o cargar un preset guardado.  
Una **pre-calibración con OPEN** opcional normaliza el S₁₁ del líquido para corregir los efectos del cable y los conectores.

### Pantalla de resultado
Una vez completas todas las mediciones, el asistente calcula **εr(f)** resolviendo un polinomio de 5to orden por frecuencia y siguiendo una rama físicamente continua. La pantalla de resultado muestra:
- Gráfico de εr (parte real ε′ y pérdidas ε″ en función de la frecuencia)
- ε′ medio y tangente de pérdidas media
- Origen de los datos por patrón (medido / importado / preset)
- Datos intermedios y criterio de selección de rama

### Exportación a PDF
Hacer clic en **Exportar PDF** en la pantalla de resultado para generar un reporte compilado con LaTeX que incluye:
- Carátula con metadatos de la medición
- Carta de Smith S₁₁ y gráfico de εr(f)
- Criterio de selección de rama
- Tabla de datos de permitividad
- Opcional: gráfico S₁₁ + mini-tabla por patrón de calibración

---

## Créditos
Este proyecto fue desarrollado como parte de los requisitos de la materia **Proyecto Final** en la UTN FRBA durante el ciclo lectivo 2026.
