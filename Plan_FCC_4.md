# Plan FCC 4 — Iteración sobre el Asistente de Caracterización de Materiales

Continuación de `Plan_FCC.md` (Stage 1/MVP ya implementado: wizard descriptor-driven,
solver de grado 5, pre-calibración OPEN, presets e imports básicos). Este plan cubre la
siguiente iteración: Debug Mode, rediseño de Reference Liquids, presets con procedencia,
fixes de pre-calibración y cursores, sweep custom para importar, selector de gráfico,
mejoras del reporte PDF, técnica simplificada de un líquido y el Characterization Package.

> **Estado:** Fases 1–6 ✅ completadas (Fases 1–2: 2026-08-19; Fases 3–5 y 5.3-bis: 2026-08-25; Fase 6: 2026-08-26). Mejoras M1–M8, M10, M11 ✅ completadas (2026-09-15). M9 (Validación E2E automatizada) pendiente.
> H13 quedó doblemente cubierto: marcha descendente (5.3-bis) + semilla del método simplificado (5.3).

Rutas abreviadas: `MC = src\NanoVNA_UTN_Toolkit\modules\material_characterization`,
`SH = src\NanoVNA_UTN_Toolkit\shared`, `DUT = src\NanoVNA_UTN_Toolkit\modules\dut_measurement`.

### Fuentes externas del material de referencia

| Qué | Copia local | Origen |
|---|---|---|
| **Antecedentes de la sonda** (campañas UTN 2015–2026, simulaciones CST 2020, papers NPL, mediciones 2026 del R60) | `D:\temp\Sonda Open Ended - Antecedentes\` | <https://drive.google.com/drive/folders/1vWChEqFr98Cv9aOmgLwDoIE1WwvhoSyR?usp=drive_link> |
| **Sonda_2026_py** (método simplificado `get_er_DUTm`, modelos de líquidos `Patrones.py`) | `C:\Workspace\python\Sonda_2026_py\` | <https://github.com/pguzmanUTN/Sonda_2026_py> |
| **Proyecto ME2 2024 / App_ME2** (MATLAB de referencia + golden values) | `medicion_fluidos\` (git-ignored) | proyecto previo de la cátedra |

Las dos primeras son **carpetas locales fuera del repositorio**: cualquier archivo que se
incorpore al programa (presets, tablas de líquidos, mediciones de prueba) debe citar en su
documentación de origen la campaña y el enlace de arriba, para que el material siga siendo
trazable si la copia local se pierde.

---

## Decisiones cerradas (2026-08-18)

1. **Debug Mode**: checkbox en Preferencias; estado global consultable desde todo el
   programa; **oculta/muestra TODOS los imports del wizard** (botones Import de
   Open/Short/Incógnita + radio "Import .s1p file" de Ref1/Ref2). Nada más (ni logging,
   ni indicador visual).
2. **Set de pruebas personal**: carpeta `test_data\` ignorada por git — **YA ENTREGADO**
   (ver `test_data\README.md`): set 2026 sonda 21 mm remuestreado a 201 pts, 1 MHz–1.5 GHz.
3. **Presets predefinidos**: mediciones **2026 (sonda 21 mm y 3 mm) + simulación CST 2020**
   (convertida de `.mat`), con `PRESETS.md` de origen.
4. **Líquidos de los desplegables**: los realmente usados por el grupo a través de los años
   + con respaldo NPL: **Agua destilada, IPA, Etanol, Metanol**. Parámetros desde
   **NPL Report MAT 23 (Gregory & Clarke 2012)**, contrastados con los XLSX de
   `D:\temp\Sonda Open Ended - Antecedentes\Permitividad en liquidos patrones - NPL\`.
   `Sonda_2026_py\Patrones.py` solo como referencia secundaria de implementación.
5. **PDF**: el checkbox de mediciones por paso las incluye **dentro del PDF**.
6. **Método de un líquido**: **2 técnicas en el registry** (no 3). La completa adopta el
   simplificado como **semilla** del quíntico + overlay de **cross-check**; la simplificada
   ofrece **"Extender a método completo"** (mide solo IPA y recalcula).
7. Plan y tarjetas en archivos nuevos: `Plan_FCC_2.md` + `Tareas_Trello_2.md` (ambos
   git-ignored por los patrones existentes).
8. **(2026-08-19)** **Sweep custom en Debug Mode**: con Debug ON, el Step 1 permite escribir
   un rango de frecuencias y una cantidad de puntos arbitrarios, fuera de los limites del
   nanoVNA conectado, para que los `.s1p` de otras campanas se puedan importar sin chocar
   con la validacion de grilla. Va en la **Fase 2** (tarea 2.8).

---

## Hallazgos clave que condicionan el plan

| # | Hallazgo | Dónde |
|---|---|---|
| H1 | El bug de pre-cal al re-medir tiene causa raíz triple: el S11 del OPEN nunca se persiste (`_open_data` es local al closure del diálogo); `_on_measure`/`_on_import`/`_load_preset` pisan la medición con datos crudos sin re-normalizar; y "Quitar pre-cal" queda visible y restaura datos viejos | `MC\ui\wizard_methods_window\steps\standard_screen.py` L891, L933–944, L661–676, L578–649, L449–469, L172–200 |
| H2 | Cursores de resultados: `markers/linked` default `"true"` (L493) y ambos arrancan hardcodeados en índice 0 (L403–404); los índices guardados se leen (L402) pero se ignoran | `MC\ui\measurement_main_window\measurement_main_window.py` |
| H3 | "Generate PDF Report" compila LaTeX 100 % en el hilo de UI, sin feedback ni try/except; el exporter de characterization es un clon del de DUT | `MC\...\export\pdf_preview_dialog.py` L867–907; `DUT\exporters\export\graph_preview_dialog.py` L1113–1140 |
| H4 | "Save as preset…" no sugiere nombre (`QInputDialog.getText` sin `text=`); `_load_preset` NO valida grilla (el import sí, estrictamente) | `standard_screen.py` L339–341, L449–469 vs L613–639 |
| H5 | No existe infraestructura Módulo/Fase en characterization; el patrón probado está en DUT (`graph_type` Smith/Magnitude/Phase) | `DUT\ui\graphics_windows\graphics_utils\graphics_utils.py` L88/L159/L204/L1214 |
| H6 | "Import Characterization Package" y los kits de la welcome son stubs que solo loguean | `MC\ui\characterization_welcome\characterization_welcome.py` L362–397 |
| H7 | La mayoría de los `.s1p` de UTN 2021/2024 contienen **εr calculada, no S11** — jamás usarlos como presets. Los válidos: 2026 (R60, MA), CST 2020 (`ws_patrones_2020.mat`), App_ME2/Kupce 2024 | inventario antecedentes |
| H8 | El "método incompleto" = `get_er_DUTm` de `C:\Workspace\python\Sonda_2026_py\funciones.py` L90–107: fórmula cerrada baricéntrica (invariancia de razón cruzada bajo Möbius), ec. (18) de Higa/Cismondi/Grass 2016. Defectos del repo a NO portar: chequeo con agua tautológico, `Er_aire` ignorado en método completo, sin filtro de pasividad | análisis Sonda_2026_py |
| H9 | El About carga `README.md`/`README_ES.md` de la raíz según parámetro de idioma; characterization y DUT comparten el mismo diálogo (`DUT\ui\utils\menu\help_menu\help_menu.py` L93–143). El problema es de **contenido desincronizado** de los dos README, no de código | menu_builder.py L83–92 |
| H10 | Debug Mode: no hay config manager; el patrón del proyecto es `QSettings` + INI vía `SH\utils\resources\settings_utils.py::get_settings` | preferencias en `SH\utils\preferences\` |
| H11 | El wizard funciona sin device (`vna_device=None`), con límites default 50 kHz–1.5 GHz y puntos `[11,51,101,201,301,401,501,1023]` | `config_screen.py` L44–54 |
| H13 | **El tramo de muy baja frecuencia envenena la selección de rama.** Con los `.s1p` 2026 completos (2000 pts desde 1 MHz) el solver devuelve εr≈171 en vez de ≈15.6 a 0.5 GHz. Causa: por debajo de ~10 MHz los cuatro patrones son casi indistinguibles, la razón cruzada queda mal condicionada y a 1 MHz sobrevive **una sola** raíz "física" (33.1−19.7j) que es falsa; la semilla se ancla ahí y el tracking arrastra la rama equivocada por toda la banda. Verificado: empezando en **≥10 MHz** el mismo set da 15.59−9.64j @0.5 GHz y 9.55−8.95j @1 GHz. La rama correcta SÍ está entre los candidatos, solo no se elige. Que el set de 201 pts de `test_data\` acierte es suerte del tracking, no robustez | `algorithms/permittivity_solver.py` semilla L206–208, tracking L209–222 |
| H12 | Claves i18n faltantes en `characterization_wizard.json` (en/es): `source_title/measure/import/preset`, `preset_empty`, `save_preset`, `delete_preset`; botón dev "Import" hardcodeado en inglés | `standard_screen.py` L264–306, L482 |

---

## FASE 1 — Debug Mode + fixes rápidos ✅ COMPLETADA (2026-08-19)

Implementada, verificada headless y **probada y aprobada por el usuario el 2026-08-19**.
Los sub-apartados de abajo describen **cómo quedó**, no lo que falta hacer.

| Ítem | Estado | Archivos |
|---|---|---|
| 1.1 Checkbox Debug Mode + helper global | ✅ | `SH\utils\preferences\debug_mode.py` (nuevo), `preferences.py` |
| 1.2 Gating de imports + import del OPEN en pre-cal | ✅ | `standard_screen.py` (se eliminó `_DEV_IMPORT_VISIBLE`) |
| 1.3 Cursores independientes | ✅ | `measurement_main_window.py` |
| 1.4 Feedback del PDF (characterization **y** DUT) | ✅ | `SH\utils\export\pdf_generation_task.py` (nuevo), ambos exporters y preview dialogs |
| 1.5 Nombre precargado del preset | ✅ | `standard_screen.py::_suggested_preset_name` |
| i18n de las claves faltantes (H12) | ✅ | `characterization_wizard.json` en/es (+10 claves), `dut_measurement_features.json` en/es |

Verificado headless con `test_data\`: imports solo con Debug ON; pre-cal por import aplica
`s11/s11_open` correctamente; cursores nacen en 41/44 y se mueven por separado; PDF compila
en worker (2.6 s) con el event loop respondiendo. El solver reproduce el etanol:
23.36−j3.54 @0.1 GHz, 15.53−j9.64 @0.5 GHz, 9.38−j8.60 @1 GHz.

**Pendiente conocido (Fase 3):** re-medir o re-importar un paso con pre-calibración activa
sigue perdiendo la normalización (H1) — el import del OPEN solo hace testeable el flujo.



### 1.1 Checkbox "Enable Debug Mode" en Preferencias ✅
- `SH\utils\preferences\debug_mode.py` **(nuevo)** — única fuente de verdad:
  `is_debug_enabled()` / `set_debug_enabled()` sobre `Preferences/debug_mode` en
  `preferences.ini` (default `false`). Nadie más repite el par de rutas exe/dev.
- `SH\utils\preferences\preferences.py`: fila "Debug Mode: [x] Enable" debajo de
  Theme/Language, con tooltip que explica qué habilita; `apply_preferences` llama al nuevo
  `change_debug_mode`; el diálogo pasó de `setFixedSize(340, 260)` a `(340, 330)`.
- **Desvío respecto del diseño**: los textos quedaron hardcodeados en inglés, igual que
  "Theme:", "Language:", "Apply" y "Close" — ese diálogo no usa JSON de recursos para nada,
  así que meterlo solo para esta fila habría sido incoherente.
- Refresco: las pantallas del wizard se reconstruyen al navegar
  (`steps_manager.update_step_screen`), así que leer `is_debug_enabled()` en el build de
  cada pantalla alcanza; no hizo falta señal/observer.

### 1.2 Gating de los imports del wizard ✅
- `standard_screen.py`: eliminado `_DEV_IMPORT_VISIBLE`; `build_standard_screen` lee
  `debug_mode = is_debug_enabled()` una vez y con eso decide:
  - botón "Import .s1p file" de Open/Short/DUT,
  - radio "Import .s1p file" de Ref1/Ref2 (el `QButtonGroup` ya tolera que falte el id 1),
  - alto del cuadro *Data source*: 178 px con import, 152 px sin él.
- **Diálogo de pre-calibración**: botón **"Import OPEN .s1p"**, el único paso que antes no
  se podía ejercitar sin sonda. El render del OPEN se factorizó en `_accept_open(freqs,
  s11, trace_color)`, compartido por medir (rojo) e importar (ámbar).
- **Extra no previsto**: la lectura y validación de `.s1p` se unificó en
  `_ask_s1p_matching_sweep(wizard, std_texts, dialog_title=None)`, así los cuatro puntos de
  import aplican exactamente el mismo contrato de grilla. Es el punto donde engancha la
  tarea **2.8** (sweep custom).

### 1.3 Cursores independientes en Permittivity Results (H2) ✅
- `measurement_main_window.py::_setup_markers`:
  - default de `markers/linked` → `"false"`;
  - `_saved_index()` restaura `markers/index_1|2` del INI (que antes se leían y se
    descartaban), con clamp a `[0, n-1]`; sin valores guardados los cursores nacen en
    `n//3` y `2n//3`;
  - el estado de link se lee **antes** de construir los sliders, para que los handles y los
    cursores arranquen coherentes cuando el usuario sí eligió enlazarlos.
- El toggle "Link/Unlink cursors" del menú contextual quedó igual.

### 1.4 Feedback visual en Generate PDF Report (H3) ✅
- `SH\utils\export\pdf_generation_task.py` **(nuevo)**, compartido por ambos módulos:
  - `GeneratingButton` — guarda texto/estilo/enabled, pone el botón en ámbar con
    "Generating report…" deshabilitado y hace `repaint()` (el handler sigue corriendo antes
    de volver al event loop; sin el repaint no se vería), y restaura al terminar.
  - `PdfCompileTask(QThread)` — corre un callable y emite `completed(success, error)`.
- **Reparto de trabajo por el riesgo de matplotlib** (ver Riesgos §5): los exporters se
  partieron en dos pasos y los diálogos rasterizan en el hilo de UI y solo mandan LaTeX al
  worker:
  - `PermittivityExporter.render_images()` + `.compile_pdf()`;
  - `LatexExporter.render_images()` + `.compile_document()`;
  - `export_to_pdf` se conservó en ambos como wrapper bloqueante para otros llamadores.
- Los dos `_generate_pdf` (characterization y DUT) usan `tempfile.mkdtemp()` + limpieza en
  el callback, guardan la task en `self._pdf_task` para que no la recolecte el GC, y ahora
  ambos reportan error con `QMessageBox` (characterization no tenía try/except).
- **Desvío**: no se usó `setOverrideCursor(WaitCursor)`; con la compilación fuera del hilo
  de UI la ventana sigue viva y el cursor de espera daría una señal equivocada.
- i18n: `generating_report` agregado en `dut_measurement_features.json` (en/es) y expuesto
  como `pdf_preview_generating_report` por `dut_resource_loader.py`.

### 1.5 Nombre precargado en "Save as preset…" (H4) ✅
- `standard_screen.py::_suggested_preset_name(wizard, descriptor, standard)` genera, p.ej.:
  ```
  water_open_coax_liquids_22.0C_1MHz-1.5GHz_201pts_precal_20260819-153000
  ```
  líquido · técnica · temperatura · rango · puntos · `precal` si la medición está
  normalizada · timestamp; sanitiza los caracteres inválidos de nombre de archivo. Se pasa
  como `text=` de `QInputDialog.getText`.

**Verificación Fase 1 — hecha (2026-08-19)**: pruebas headless (`QT_QPA_PLATFORM=offscreen`)
sobre `test_data\`:
- Debug OFF → ningún import en pasos 2 y 4; Debug ON → aparecen en ambos.
- Import del OPEN en pre-cal → `set_measurement` guarda exactamente `s11_liq / s11_open` y
  el original queda en `_precal_originals`.
- Cursores restaurados en 41 y 44; mover el 1 al índice 10 deja el 2 en 44.
- PDF: renderizado en UI + compilación en worker, 2.6 s, event loop respondiendo, 510 KB.
- **Cadena completa del asistente** importando los 5 pasos → etanol 23.36−j3.54 @0.1 GHz,
  15.53−j9.64 @0.5 GHz, 9.38−j8.60 @1 GHz (coincide con la curva Debye real).


---

## FASE 2 — Reference Liquids en Step 1 + presets con procedencia ✅ COMPLETADA (2026-08-19)

Los sub-apartados describen el diseño; esta tabla, lo que quedó.

| Ítem | Estado | Archivos |
|---|---|---|
| 2.1 Etanol y metanol (NPL MAT 23) | ✅ | `algorithms/reference_liquids.py` (+ modelo `DEBYE_GAMMA`) |
| 2.2 Dos desplegables de líquido en Step 1 | ✅ | `steps/session_liquids.py` (nuevo), `config_screen.py`, `standard_screen.py`, `step_sidebar.py` |
| 2.3 Combo de medición predefinida + eliminar | ✅ | `config_screen.py` |
| 2.4 Metadata de presets (sidecar JSON) | ✅ | `calibration/preset_store.py` (nuevo) |
| 2.5 Presets bundled + `PRESETS.md` | ✅ | `preset_liquids/_tools/build_bundled_presets.py` (nuevo), 16 presets |
| 2.6 Validación/remuestreo al cargar preset | ✅ | `standard_screen.py::_load_preset_into_step` |
| 2.7 "Save as preset…" junto a Measure | ✅ | `standard_screen.py` (Delete preset eliminado del paso) |
| 2.8 Sweep custom en Debug Mode | ✅ | `config_screen.py`, `measure_runner.py`, `standard_screen.py` |

**Desvíos respecto del diseño**

- **2.1** — se usa interpolación polinómica en temperatura (igual que agua e IPA), no
  "fila más cercana": ni etanol ni metanol cambian de ecuación dentro de 10–50 °C, así que
  interpolar está bien definido. Queda documentado en el código que un líquido que SÍ cambie
  de ecuación con la temperatura debe usar fila más cercana.
- **2.3** — el combo de presets guarda el *nombre* en `userData` y muestra el `display_name`
  del sidecar; filtra por líquido y siempre incluye los presets legados sin metadata.
- **2.5** — se agregaron **16** presets (11 mediciones 2026 + 5 CST 2020), ~1.1 MB. Las CST
  traen |S11| levemente >1 en algunos puntos: es un artefacto del post-proceso de CST
  (verificado contra `pol2complex.m`), documentado en su metadata.
- **2.7** — el guardado ahora está en TODOS los pasos (Open/Short/incógnita incluidos), no
  solo en los de referencia, y pasa por `preset_store` (sidecar + PRESETS.md).
- **2.8** — además del sweep libre se agregó el botón **"Usar el barrido del archivo"** en el
  aviso de grilla (tarjeta 14) y una **guarda al medir**: `run_s11_sweep` ya no recorta en
  silencio un sweep fuera de las capacidades del equipo, lo rechaza con un mensaje explícito.

**Verificación (headless, `QT_QPA_PLATFORM=offscreen`)**

- Etanol y metanol reproducen la fila tabulada a 25 °C (Δ<0.04 en εs), εr' monótona
  decreciente y pérdidas siempre negativas; avisa al extrapolar fuera de 10–50 °C.
- Step 1: los dos combos ofrecen los 4 líquidos; cambiar Ref2 a etanol refiltra sus presets;
  duplicar el líquido muestra el aviso y **bloquea Next**; T=55 °C avisa que IPA se extrapola.
- Preset de 2000 pts en un sweep de 201 → ofrece remuestreo y lo aplica con error 0.0 vs la
  interpolación de referencia.
- Guardar desde un paso crea `.s1p`+`.json` con líquido/rol/técnica/temperatura correctos y
  agrega la fila en `PRESETS.md`; borrarlo la saca de la tabla y lo registra en el log.
- Debug ON: puntos editables, sweep 2000 pts / 1 MHz–2 GHz aceptado, aviso de que el equipo
  no puede medirlo, y los 5 pasos importados a 2000 puntos → `calibration_complete`.

**⚠ Consecuencia inesperada — ver H13.** Con el sweep completo desde 1 MHz el resultado de
permitividad es incorrecto (rama equivocada). No es un defecto introducido por la Fase 2:
es una debilidad previa del tracking que esta fase recién hace alcanzable. Mientras no se
resuelva (**5.3-bis**), configurar el barrido **desde 10 MHz o más**.


### 2.1 Librería de líquidos: agregar Etanol y Metanol
- `MC\algorithms\reference_liquids.py`: sumar `ethanol` (Debye-γ, NPL MAT 23 notas Gregory)
  y `methanol` (Debye simple) con tablas por temperatura, `validated=False` + `source` como
  prevé Plan_FCC S2.1, convención de signos existente (`Im ≤ 0`).
- **Fuente**: NPL Report MAT 23 (PDF en `D:\temp\...\Permitividad en liquidos patrones - NPL\`).
  Test de contraste contra los XLSX de esa carpeta (agua y propan-2-ol) y, como referencia
  secundaria, contra `Sonda_2026_py\Patrones.py` (etanol 25 °C: es=24.43, eh=4.505,
  fr=0.964 GHz, γ=0.056; metanol 25 °C: es=32.66, e_inf=5.563, fr=3.141 GHz).
- Estrategia de temperatura: fila tabulada más cercana + warning fuera de rango (no
  interpolar entre filas: para etanol/IPA la *ecuación* cambia según el rango de T).

### 2.2 Step 1: dos desplegables de líquido de referencia
- `config_screen.py` L155–169: reemplazar los `QLabel` por, para cada referencia (i=1,2):
  `QComboBox` de líquidos (agua, IPA, etanol, metanol) — defaults **Ref1=agua, Ref2=IPA** —
  + a su derecha el combo de mediciones predefinidas (2.3) + botón eliminar (2.3).
- Validaciones: Ref1 ≠ Ref2 (bloquear Next con mensaje); warning si la temperatura del
  Step 1 queda fuera del rango tabulado del líquido.
- `_commit` (L270–287): pasar las claves seleccionadas a
  `perm_calibration.set_reference_liquids(key1, key2)` (hoy manda los defaults del
  descriptor). Persistir en la sesión (`wizard.ref_liquid_keys`).
- Efectos aguas abajo (verificar, no deberían requerir cambios): curvas indicativas en
  `_render` (L733–743), `pattern_constants`, textos de pasos 4/5 (títulos deben mostrar el
  líquido elegido, no "Water"/"IPA" fijos → `step_sidebar._step_name` y títulos de
  `standard_screen`).

### 2.3 Combo de "medición predefinida" por referencia (default **None**) + eliminación
- Para cada referencia, combo poblado con los presets de `MC\calibration\preset_liquids\`
  **filtrados por `liquid_key`** (necesita metadata → 2.4). Opción inicial `None`.
- Al elegir un preset: se guarda en la sesión (`wizard.preset_preload[std_key] = name`).
  Al construirse el paso 4/5, `standard_screen` detecta el preload, carga el `.s1p`
  (validando grilla, ver 2.6), lo setea como medición del paso y lo muestra como "cargado
  desde preset X" — el usuario puede igualmente re-medir encima.
- Botón **eliminar** (🗑 al lado de cada combo, o un único botón "Manage presets…"):
  confirma y borra `.s1p` + sidecar JSON + marca la fila como eliminada en `PRESETS.md`.
  **Se elimina `Delete preset` de los pasos de medición** (`standard_screen.py` L298–306,
  L367–382 y su rama en `_on_source_changed`).
- El radio "Use saved preset" de los pasos 4/5 puede quedar (útil), pero su combo se
  refresca con los mismos datos y ya no tiene delete.

### 2.4 Metadata de presets: sidecar JSON
Un `.s1p` no lleva metadata → agregar `<nombre>.json` junto a cada `<nombre>.s1p`:
```json
{
  "schema_version": 1,
  "display_name": "Agua destilada — R60 sonda 21mm (2026-06-25)",
  "liquid_key": "water",            // water|ipa|ethanol|methanol|air|short|unknown
  "role": "reference",              // open|short|reference|dut
  "source": "measured",             // measured|imported|simulated
  "instrument": "Copper Mountain R60",
  "probe": "open-ended coax 21 mm",
  "temperature_c": 22.0,
  "acquired": "2026-06-25T14:44:00",
  "saved": "2026-08-18T15:30:00",
  "technique": "open_coax_liquids",
  "points": 201, "f_start_hz": 1000000, "f_stop_hz": 1500000000,
  "precal_open_applied": false,
  "origin_note": "Remuestreado de 2000 pts 1MHz-2GHz"
}
```
- Módulo nuevo `MC\calibration\preset_store.py`: `list_presets(liquid_key=None)`,
  `load_preset(name)`, `save_preset(name, freqs, s11, meta)`, `delete_preset(name)`,
  `append_presets_md(meta)`. Centraliza lo que hoy está disperso en `standard_screen.py`
  (`_get_preset_path` L57–60, `_refresh_preset_combo` L63–74, save/delete/load).
- Presets legados sin JSON (p.ej. `preset_distilled_water.s1p`): tratarlos como
  `liquid_key=unknown` y mostrarlos en ambos combos con sufijo "(sin metadata)".

### 2.5 Presets predefinidos (bundled) + `PRESETS.md`
- Convertir e incluir en `MC\calibration\preset_liquids\`:
  - **2026 sonda 21 mm** (6): `water_r60p21_2026`, `ipa_r60p21_2026`, `ethanol_r60p21_2026`,
    `open_air_r60p21_2026`, `short_r60p21_2026`, `water_deep35mm_r60p21_2026`
    — desde `D:\temp\...\Mediciones 2026 con sonda 21 mm y 3 mm\` (MA→RI vía skrf).
  - **2026 sonda 3 mm** (5): ídem con sufijo `_r60p3_2026` (1181 pts, 100 MHz–6 GHz).
  - **CST 2020** (4+1): `sim_cst2020_{open,short,water,alcohol}` + un MUT representativo
    (`sim_cst2020_muscle000`) — extraídos de
    `D:\temp\...\UTN 2020 - Simulacion  sonda CST para medicion materiales\MATLAB\Calculo Er\ws_patrones_2020.mat`
    (variables `modS11*/phaseS11*` → complejo → `.s1p`; 100 pts, 100 MHz–10 GHz).
    `source="simulated"` y prefijo `sim_` para que jamás se confundan con mediciones.
  - Script one-shot de conversión en `MC\calibration\preset_liquids\_tools\` (o en `tests\`),
    commiteado para trazabilidad.
- **`PRESETS.md`** en `preset_liquids\`: tabla por preset — nombre, líquido, rol, origen
  (campaña/instrumento/sonda/fecha), rango, puntos, fuente (medido/importado/simulado),
  notas. Sembrado con los bundled; **`preset_store.save_preset` agrega una fila en cada
  guardado** desde el asistente (y `delete_preset` la tacha o la mueve a una sección
  "Eliminados").
- Advertencia documentada en `PRESETS.md`: los `.s1p` de UTN 2021/2024-εr NO son S11 (H7).

### 2.6 Robustez de carga de presets (H4)
- `_load_preset`/preload de Step 1: validar grilla contra el sweep configurado con el mismo
  criterio que `_on_import` (L613–639). Si no coincide: ofrecer **remuestear** (interp
  Re/Im, como `Sonda_2026_py\Touchstone.resamplear`, citando fuente) con warning, o abortar.
  Esto además permite usar los presets 2026 de 2000/1181 pts con cualquier sweep configurado.

### 2.7 Mover "Save as preset…" al lado de "Measure"
- `standard_screen.py`: sacar `btn_save_preset` del cuadro "Data source" (L288–296) y
  ubicarlo a la derecha del botón Measure/Import principal. Habilitado solo cuando el paso
  tiene medición (`already`), como hoy. Guarda **lo que el paso tiene medido/cargado**
  (datos crudos + flag `precal_open_applied` si corresponde) vía `preset_store`.
- Con Fase 2 completa, el cuadro "Data source" queda: Measure / Import (debug) / Use preset,
  sin botones de save/delete.
- i18n: agregar TODAS las claves faltantes (H12) en `SH\resources\material_characterization\{en,es}\characterization_wizard.json`.

### 2.8 Sweep custom en Debug Mode (destraba el import de cualquier `.s1p`)

> Trello: tarjeta **13** (sweep custom) y tarjeta **14** ("usar el sweep del archivo").

**Problema.** El import exige que el archivo coincida **exactamente** con el sweep
configurado: misma cantidad de puntos y mismos extremos, con tolerancia de 1e-3 Hz
(`_ask_s1p_matching_sweep`, ex `_on_import` L613–639). Pero el Step 1 no deja configurar
cualquier sweep: los puntos salen de una lista cerrada y el rango se clampea a lo que
declara el nanoVNA conectado (`config_screen.py::_device_caps` L44–54 y `_clamp_hz` L241,
H11). Resultado: con un nanoVNA enchufado, un `.s1p` de 2000 pts / 1 MHz–2 GHz del R60 —o
de cualquier otra campaña— **no hay forma de importarlo**, porque no existe un sweep
alcanzable que lo describa. Por eso el set de `test_data\` tuvo que remuestrearse a
201 pts / 1 MHz–1.5 GHz.

**Solución.** Con Debug ON, el Step 1 deja de estar limitado por el device:
- **Puntos**: `wizard.points_input` pasa de `QComboBox` cerrado a editable (o se cambia por
  un `QSpinBox` de rango amplio, p.ej. 2–20000). Con Debug OFF sigue siendo la lista de
  `valid_datapoints` del equipo, tal cual hoy.
- **Frecuencias**: `_clamp_hz` (L241) y `_apply_freq_range` (L235) dejan de recortar contra
  `min_hz`/`max_hz` del device; el `QDoubleSpinBox` ya admite hasta 1e12 Hz (L106, L112).
- **Aviso visible**: el `info_card` del device (L88–96) muestra, cuando el sweep excede lo
  que el equipo soporta, algo como *"Debug Mode: sweep fuera de las capacidades del
  {device} — solo válido para importar archivos, no para medir"*. Nueva clave i18n
  `config.debug_sweep_warning` en en/es.
- **Guarda al medir**: `measure_runner.run_s11_sweep` (L43) debe rechazar con un mensaje
  claro —no un error de bajo nivel— si el sweep configurado excede el device. Medir con un
  sweep imposible no es el caso de uso; importar sí.

**Extra que lo hace cómodo — "Adoptar sweep del archivo".** Cuando el import falla por
grilla, el `QMessageBox` de `import_error_freq_mismatch` gana (solo en Debug ON) un botón
**"Usar el sweep del archivo"** que escribe start/stop/points de ese `.s1p` en la sesión del
wizard y reintenta el import. Evita tipear a mano 2000 / 1 MHz / 2 GHz y, sobre todo, evita
el error silencioso de tipear mal un extremo. Como `_ask_s1p_matching_sweep` ya es el único
punto de validación (Fase 1), el cambio entra en un solo lugar para los cuatro imports.

**Interacción con 2.6.** Son complementarios y conviene decidirlo junto: 2.6 remuestrea el
archivo para que entre en el sweep configurado; 2.8 adapta el sweep al archivo. Para un
`.s1p` de otra campaña **2.8 es el camino correcto** (no interpola, no inventa datos);
2.6 queda para cuando se quiere forzar una grilla común entre archivos heterogéneos.
Regla propuesta: ofrecer primero "usar el sweep del archivo" y dejar el remuestreo como
segunda opción, siempre con warning.

**Cuidado.** Todos los estándares tienen que terminar en la **misma** grilla o
`compute_calibration` falla por diseño (no interpola). Si el usuario cambia el sweep a mitad
del asistente con pasos ya medidos, hay que avisar y ofrecer descartar las mediciones
previas; el `epsilon_result` ya se invalida solo.

**Archivos**: `config_screen.py` (widgets, `_device_caps`, `_clamp_hz`, `_apply_freq_range`,
`_commit`), `standard_screen.py::_ask_s1p_matching_sweep` (botón de adopción),
`measure_runner.py` (guarda), `characterization_wizard.json` en/es (claves nuevas).

**Verificación Fase 2**: combos muestran 4 líquidos; elegir etanol como Ref2 y verificar
curva indicativa y solver; preset combo filtra por líquido; preload desde Step 1 deja el
paso 4 "medido"; guardar preset desde un paso → aparece `.s1p`+`.json` y fila en
`PRESETS.md`; eliminar desde Step 1 la borra; cargar preset de grilla distinta ofrece
remuestreo. Test unitario: etanol/metanol vs XLSX NPL (tolerancia 1e-3 relativa).
Para 2.8: con Debug ON y el nanoVNA conectado, configurar 2000 pts / 1 MHz–2 GHz e importar
los crudos de `test_data\sonda21_2026\original\` sin remuestrear; con Debug OFF el Step 1
vuelve a estar limitado por el equipo.

---

## FASE 3 — Pre-calibración correcta + selector de gráfico ✅ COMPLETADA (2026-08-25)

### 3.1 Fix del bug de re-medición con pre-cal (H1)
Modelo de estado nuevo en el wizard (sesión):
```python
wizard._precal_open[std_key]      = (freqs_open, s11_open)   # el OPEN de normalización, persistido
wizard._precal_originals[std_key] = (freqs, s11_raw)         # el crudo del líquido (ya existe)
```
- `_do_apply` del diálogo (L933–944): además de lo actual, guardar `_precal_open[std_key]`.
- **Regla única de escritura** — helper `_store_measurement(wizard, std_key, freqs, s11_raw)`:
  1. guarda el crudo en `_precal_originals` (si hay pre-cal activa),
  2. si `std_key in _precal_open` y las grillas coinciden → `s11 = s11_raw / s11_open`,
  3. `perm_calibration.set_measurement(std_key, freqs, s11)`, invalida `epsilon_result`.
  Usarlo desde `_on_measure` (L661–676), `_on_import` (L578–649), `_load_preset` (L449–469)
  y el preload de Step 1. → re-medir con pre-cal activa **re-aplica** la normalización.
- Si la grilla del OPEN no coincide con la nueva medición: warning + descartar la pre-cal
  (limpiar `_precal_open/_precal_originals` del paso y ocultar "Quitar pre-cal").
- `_delete_precal` (L192–202): restaurar el crudo **actual** (que ahora siempre está
  sincronizado) y limpiar ambos dicts del paso.
- Persistir también el open de pre-cal en disco junto a `probe_results\` (p.ej.
  `precal_open_ref1.s1p`) para el Characterization Package (Fase 6).

### 3.2 Checkbox "Ver sin pre-calibración"
- En pasos con pre-cal activa, checkbox junto al de "Show indicative reference"
  (hoy `fig.text` picker, L516–536 — misma mecánica o migrar ambos a `QCheckBox`, preferible).
- **Solo afecta la visualización**: `_render` recibe `show_raw` y elige entre
  `_precal_originals[key]` y la medición normalizada (o dibuja ambas: normalizada sólida +
  cruda punteada gris, que es más informativo). El solver SIEMPRE usa lo almacenado en
  `perm_calibration` (normalizado si hay pre-cal).

### 3.3 Selector Smith / Módulo / Fase en cada paso (y en el diálogo de pre-cal)
- Nuevo `MC\ui\wizard_methods_window\charts\s11_chart_modes.py` — módulo-local (regla de
  no tocar DUT), inspirado en el patrón de `DUT\...\graphics_utils.py` (H5):
  - `render_smith(ax, ...)` (delegando en lo actual), `render_magnitude(ax, freqs, s11)`
    (|S11| en dB vs f) y `render_phase(ax, freqs, s11)` (fase en grados, con `np.unwrap`
    y auto-rango de eje estilo `Sonda_2026_py\Touchstone._rango_fase_amigable`, citado).
  - Las curvas indicativas de referencia y los marcadores Open/Short se re-expresan por
    modo (indicativa → |S11| y fase teóricas; Γ=±1 → 0 dB / 0° ó 180°).
- `standard_screen.py`: `QComboBox` "Chart: Smith | Magnitude | Phase" sobre el gráfico;
  `_render` (L698–770) despacha según el modo. Persistir el último modo en
  `characterization_chart_config.ini` (`[wizard_chart] mode=smith`).
- Mismo combo en `_open_precal_dialog` (L808–950) para el gráfico del OPEN.
- El paso Resultados no cambia (su gráfico es εr, no S11).

**Verificación Fase 3**: con `test_data\`: importar Ref1 → pre-cal (importando el OPEN con
Debug ON) → gráfico normalizado → re-importar Ref1 → **sigue normalizado**; "Quitar
pre-cal" restaura el crudo actual; checkbox alterna/superpone crudo; selector cambia
Smith/|S11|/fase en pasos y en el diálogo de pre-cal y el modo persiste entre pasos.

---

## FASE 4 — Resultados, procedencia y reporte ✅ COMPLETADA (2026-08-25)

### 4.1 Revisión de la documentación del criterio de selección de Epsilon
- Estado: `MC\algorithms\permittivity_solver.py` SÍ documenta el criterio (docstring
  bilingüe L164–178; semilla L206–208 = raíz de menor |Im| del primer punto; tracking
  L209–222 = polyfit ventana 5 orden ≤2 + vecino más cercano; `_physical_mask` L138–151:
  `Re>0`, `Im≤tol`).
- Tareas: verificar que el texto coincide 1:1 con el código tras los cambios de Fase 5
  (la semilla cambia); documentar el criterio también donde lo ve el usuario: tooltip/nota
  en `result_screen._build_intermediate` (L259) y sección "Criterio de selección" en el PDF.

### 4.2 Procedencia medido/importado/preset
- `MC\calibration\permittivity_probe_calibration.py::set_measurement`: parámetro
  `source: str` (`measured|imported|preset:<name>`) almacenado por estándar (+ persistido
  en un JSON junto a `probe_results\`).
- Mostrarlo en: info strip de `MeasurementMainWindow` (`_build_info_strip` L128) y en el
  **PDF** (tabla de líquidos de referencia: "Agua destilada — medido el …" /
  "IPA — importado de <archivo>" / "preset <nombre>"). Cumple el requisito del reporte.

### 4.3 Checkbox "Incluir mediciones de cada paso" en el PDF
- `latex_export_setup_dialog.py`: `QCheckBox` (default off) → flag a
  `PermittivityExporter.export_to_pdf`.
- `permittivity_exporter.py::_create_latex_document` (L245): si el flag está activo, una
  sección por estándar (Open, Short, Ref1, Ref2, Incógnita): gráfico S11 (Smith + |S11|,
  generados con las figuras del wizard/manager) + mini-tabla (puntos, rango, fuente
  medido/importado, pre-cal aplicada sí/no, timestamp).
- Los datos salen de `perm_calibration.get_measurement(...)` + metadata de 4.2.

### 4.4 Unificación de READMEs de Help/About (H9)
- Unificar **contenido y estructura** de `README.md` y `README_ES.md` (raíz): mismas
  secciones, mismas imágenes, traducción 1:1; incluir el modo characterization en ambos.
- Afecta a los tres consumidores del mismo diálogo (`help_menu.py`): characterization
  (`menu_builder.py` L83–92), DUT (`graphics_window.py` L320–324) y cualquier otro.
- Mejora opcional (M6): una sola entrada "About" que respete `Preferences/language` en
  lugar de dos entradas fijas EN/ES.

**Verificación Fase 4**: PDF con checkbox ON contiene las 5 secciones con procedencia
correcta (mezclar: ref1 importada, ref2 preset); About EN y ES muestran el mismo contenido
traducido.

---

## FASE 5 — Técnica simplificada (un líquido de referencia) ✅ COMPLETADA (2026-08-25)

Implementada en cuatro commits (uno por tarea), verificada headless de punta a punta y
pusheada. Tarjetas de Trello **23–26** hechas. Documentación para el equipo:
- Guía de estudio (repo): `docs\metodo_simplificado.md`
- Guía visual con diagramas (artifact, compartible desde su menú):
  <https://claude.ai/code/artifact/6995aa2f-098d-4b7e-875e-66cd3ee355e1>

| Ítem | Estado | Commit | Archivos clave |
|---|---|---|---|
| 5.1 Solver de fórmula cerrada + tests | ✅ | `956c726` | `algorithms\simplified_solver.py`, `tests	est_simplified_solver.py` |
| 5.2 Técnica en el registry + ref2 opcional | ✅ | `4632183` | `techniques\open_coax_liquids_simplified.py`, `permittivity_probe_calibration.py`, `result_screen.py` |
| 5.3 Semilla del quíntico + cross-check | ✅ | `4877a0a` | `permittivity_solver.py`, `epsilon_chart.py`, `result_screen.py`, `tests	est_algorithms.py` |
| 5.3-bis Rama a baja frecuencia (H13) | ✅ | `a154e53` | `permittivity_solver.py` (previo, de otro colega) |
| 5.4 "Extender a método completo" | ✅ | `ac0ecdf` | `result_screen.py::_build_extend_to_full` |

**Números que resumen la fase** (presets 2026 sonda 21 mm, etanol como incógnita, 22 °C):
- Método simplificado: εr′ dentro del **2–6 %** del modelo NPL del etanol en 50 MHz–1.5 GHz;
  degrada fuera de esa banda (ruido abajo, radiación despreciada arriba) — trade-off documentado.
- Método completo sembrado: **23.36−j3.59 / 15.59−j9.64 / 9.55−j8.95** a 0.1/0.5/1 GHz sobre
  el barrido denso desde 1 MHz — la rama canónica, mejor que la marcha descendente sola.
- Suite del módulo: **14/14 tests** (6 nuevos del simplificado + 2 de semilla/golden H13).

Basada en H8. Fórmula (citar SIEMPRE: Higa/Cismondi/Grass 2016 ec. 18; paper IEEE
ARGENCON 2024 Henze et al.; implementación de referencia `Sonda_2026_py\funciones.py::get_er_DUTm`):

```
coef_ref = ((Γm−Γair)(Γshort−Γref)) / ((Γm−Γshort)(Γref−Γair))
coef_air = ((Γm−Γref)(Γair−Γshort)) / ((Γm−Γshort)(Γref−Γair))
ε_m = −coef_ref·ε_ref(f,T) − coef_air·ε_air          (coef_ref+coef_air = −1)
```

### 5.1 Solver ✅ COMPLETADA (2026-08-25)

Implementado en `MClgorithms\simplified_solver.py` + `tests	est_simplified_solver.py`
(6 tests, todos en verde). Desvíos/decisiones respecto del diseño:
- Recibe el objeto `ReferenceLiquid` (no la key) — consistente con `pattern_constants`.
- El golden usa los **presets bundled 2026** (commiteados) en vez de `test_data\` (local):
  εr' del etanol coincide con el modelo NPL dentro del 2–6 % en 50 MHz–1.5 GHz (mediana
  <10 % exigida); anclas de regresión 26.0 / 20.4 / 13.0 a 0.1 / 0.5 / 1 GHz (±5 %).
- Identidad de Ptolomeo (`coef_ref+coef_air=-1`) verificada a 4.5e-16 con datos reales.
- Hallazgo para 5.3: a 0.5 GHz el simplificado (20.4) queda MÁS cerca del modelo NPL (19.8)
  que el método completo (15.6) — el cross-check va a exponer esa divergencia.
- Dato real: glitch angosto ~690 MHz en la campaña 2026 (14/1001 pts con Im>0); la máscara
  de pasividad lo reporta como warning de calidad.

#### Diseño original (referencia)
- Nuevo `MC\algorithms\simplified_solver.py`: `solve_epsilon_simplified(freqs, s11_dut,
  s11_ref, s11_open, s11_short, liquid_key, temperature_c)` → εr complejo vectorizado.
  - Generalizar el líquido de referencia (NO cablear a agua como el repo).
  - Guardas: denominadores `|·|<1e-12` → NaN + warning; máscara de pasividad
    (`Re>0`, `Im≤tol`) solo como *warning* de calidad (la fórmula no tiene ramas).
  - **NO portar** el "chequeo con agua" (tautológico) ni `error_relativo_porcentual`
    con su signo confuso (H8).
- Tests: sintético (Möbius arbitraria + εr conocida → recuperación exacta) y golden con
  `test_data\` (etanol ≈ 23.4−j3.6 @0.1 GHz, 15.6−j9.6 @0.5 GHz, 9.6−j8.9 @1 GHz, tol 5 %).

### 5.2 Descriptor de la técnica ✅ COMPLETADA (2026-08-25)

Implementado según el diseño, con estas decisiones:
- `techniques\open_coax_liquids_simplified.py` (nuevo): mismos `std_key` que la técnica
  completa (open/short/ref1/dut) para que 5.4 reutilice las mediciones. Registrado en
  `techniques\__init__.py`; aparece segundo en el desplegable de la intro.
- `permittivity_probe_calibration.py`: `set_reference_liquids(ref1, ref2=None)` —
  `ref2=None` activa el modo simplificado (`is_simplified`, `required_standards`);
  `get_completion_status` cuenta solo los patrones requeridos; `compute_epsilon`
  despacha a `solve_epsilon_simplified` (sin pattern constants).
- `SimplifiedEpsilonResult` ganó la property `eps_selected` (alias de `eps`): la ventana
  de resultados, el chart y los exporters PDF consumen `f_hz`/`eps_selected`/`warnings`
  y funcionan sin cambios con ambos tipos de resultado.
- `result_screen.py`: para el resultado simplificado se oculta el bloque del quíntico y
  el override de rama, y se muestra una nota del método (fórmula cerrada, sin ramas,
  radiación despreciada) + líquido de referencia y temperatura.
- Info strip de `MeasurementMainWindow`: muestra una sola referencia cuando `ref2` es None.
- i18n: entrada `open_coax_liquids_simplified` en `characterization_methods.json` (en/es)
  y claves `simplified_*` en `characterization_wizard.json` (en/es).

Verificado headless: wizard completo con la técnica nueva (Step 1 con una sola fila de
referencia → open/short/agua/etanol importados a 2000 pts → resultado 20.43−8.17j @0.5 GHz,
nota visible, sin bloque quíntico, ventana final OK) y regresión del método completo
(14.88−9.00j @0.5 GHz con la marcha descendente). 12/12 tests.

#### Diseño original (referencia)
- `MC\techniques\open_coax_liquids_simplified.py`: pasos intro → config (UNA referencia,
  default agua) → Open → Short → Ref1 → Incógnita → Resultados. Registrar en `registry.py`.
- `config_screen.py` ya itera `descriptor.reference_standards` → con un solo standard la UI
  de Step 1 sale gratis (un combo en vez de dos).
- `permittivity_probe_calibration.py`: `get_completion_status`/`compute_epsilon` deben
  funcionar sin `ref2` (switch por técnica). `compute_epsilon` despacha al solver
  simplificado cuando la técnica lo indique.
- `result_screen.py`: para esta técnica no hay selector de rama (fórmula cerrada) —
  ocultar el bloque de raíces del quíntico y mostrar una nota del método.

### 5.3 Semilla + cross-check en el método completo ✅ COMPLETADA (2026-08-25)

Implementado según el diseño. Decisiones y hallazgos:
- `solve_epsilon_r(..., eps_seed=None)`: donde la semilla es finita, se elige la raíz más
  cercana a ella (reemplaza tanto la semilla de menor |Im| como la extrapolación polinómica);
  donde es NaN cae al tracker de siempre. Sin semilla, comportamiento idéntico al anterior.
- El manager calcula la semilla gratis en el método completo (open/short/ref1 ya medidos)
  vía `_simplified_seed()` — best-effort: si falla, sigue sin semilla.
- La semilla viaja en el resultado como `eps_crosscheck`; `EpsilonResult` ganó ese campo
  (default None, sin ruptura). Warning automático si la selección diverge >25 % (mediana)
  del cross-check en la mitad baja de la banda → señal de problema en ref2.
- **La semilla mejoró el resultado**: el set 2026 completo desde 1 MHz pasó de
  22.22/14.88/9.36 (marcha descendente sola) a **23.36/15.59/9.55** a 0.1/0.5/1 GHz — la
  rama canónica esperada por el plan. Ídem `test_data` 201 pts.
- Efecto conocido: 2 pares de puntos con salto >50 % en 2–3 MHz (zona H13, la semilla es
  ruidosa ahí); el warning de saltos existente lo reporta — es información honesta, antes
  esa zona era "suave" pero sobre una rama corrida.
- UI: checkbox "Show cross-check (simplified method)" en Resultados → overlay punteado en
  los mismos colores; convive con el override de rama vía un redibujado unificado.
  `criterion_text` actualizado (código + JSON en/es) para mencionar la semilla.
- Tests nuevos: semilla sintética (sigue la semilla, tolera NaN, sin semilla no hay
  crosscheck) + golden de regresión H13 con los presets 2026 (14/14 en verde).

#### Diseño original (referencia)
- `permittivity_solver.py::solve_epsilon_r`: aceptar `eps_seed: ndarray | None` (la curva
  del simplificado). Con semilla: en cada frecuencia la predicción del tracking es el valor
  de la semilla (y recorrer de **alta a baja frecuencia**, donde Gn es más chico y el
  simplificado es mejor — estrategia validada en `Sonda_2026_py` L296–319). Sin semilla:
  comportamiento actual. Actualizar docstring (4.1).
- `result_screen.py`: checkbox "Mostrar cross-check (método simplificado)" → overlay
  punteado de la curva simplificada en el chart de εr (`charts\epsilon_chart.py`).
  Divergencia grande entre ambas curvas a baja frecuencia = bandera de problema en IPA
  (es el único patrón que entra solo vía Gn).

### 5.3-bis Robustecer la selección de rama a baja frecuencia (H13) ✅ COMPLETADA (2026-08-25)

Descubierto al completar la Fase 2; hoy es lo que impide confiar en un import denso.

- **Semilla en la frecuencia más alta y marcha descendente.** Es donde `Gn = G0/(jωC0)` es
  menor y la inversión mejor condicionada (estrategia de `Sonda_2026_py` L296–319). Medido
  sobre el set 2026 completo: la marcha descendente da 22.2 / 14.9 / 9.4 a 0.1 / 0.5 / 1 GHz
  contra 171 / 171 / 172 de la implementación actual.
- **Detectar y excluir el tramo mal condicionado.** Marcar como `gap` las frecuencias donde
  los patrones son casi indistinguibles (p. ej. `|Γ_ref1 − Γ_ref2|` o el denominador de la
  razón cruzada por debajo de un umbral) en vez de devolver una raíz espuria con cara de
  válida. Avisar en Resultados cuántos puntos se descartaron y por qué.
- **Aviso de rama inestable**: portar `_diagnosticar_saltos` (M10) y avisar si εr' salta
  >50 % entre puntos contiguos.
- Test de regresión obligatorio: el set 2026 completo desde 1 MHz debe dar ≈15.6−9.6j a
  0.5 GHz, y el set de 201 pts de `test_data\` no debe cambiar respecto de hoy.

### 5.4 "Extender a método completo" ✅ COMPLETADA (2026-08-25)

Implementado en `result_screen.py::_build_extend_to_full` según el diseño:
- Botón "Extend to full method (2nd liquid)…" bajo la nota del método simplificado, con
  diálogo de confirmación que explica qué se conserva y qué falta.
- El click fija ref2 en la sesión (IPA por defecto; agua si ref1 ya es IPA — deben
  diferir), llama `set_reference_liquids(ref1, ref2)` (sale del modo simplificado sin
  tocar las mediciones), cambia `selected_technique_id`/`selected_method`, invalida
  `epsilon_result` y `pattern_constants`, y salta al paso ref2 de la técnica completa
  (el índice se busca en el descriptor, no está hardcodeado).
- Funciona porque ambas técnicas comparten los `std_key` (decisión de 5.2): el dispatcher
  resuelve el descriptor en cada render, así que el cambio en caliente es natural.
- Para cambiar el líquido de ref2 el usuario puede volver a Configuración, que al estar
  en la técnica completa ya muestra los dos desplegables.
- i18n: `extend_button/extend_title/extend_msg` en/es.

Verificado E2E headless: simplificado completo (20.43−8.17j @0.5 GHz) → Extender →
"Step 5/7: Reference liquid: IPA" con open/short/ref1/dut conservados → importar IPA →
resultado `EpsilonResult` con crosscheck: 23.36/15.59/9.55 a 0.1/0.5/1 GHz (rama
canónica, sembrada por la curva simplificada de la misma sesión). 14/14 tests.

#### Diseño original (referencia)
- En resultados de la técnica simplificada: botón "Extender a método completo…" →
  agrega/salta al paso Ref2 (IPA por default, seleccionable), lo mide o importa, y
  recalcula con el solver completo usando la curva simplificada como semilla.
- Implementación: `wizard` cambia `selected_technique_id` a la técnica completa
  conservando `perm_calibration` (open/short/ref1/dut ya medidos) y navega al paso Ref2.
  Requiere que los `std_key` coincidan entre ambas técnicas (open/short/ref1/dut) — diseñar
  los descriptors con las mismas claves.

**Verificación Fase 5**: con `test_data\`: técnica simplificada (open/short/agua/etanol) →
curva εr correcta sin selector de rama; técnica completa con cross-check ON → dos curvas
casi superpuestas; "Extender" desde la simplificada importando IPA → resultado del método
completo. Tests unitarios de 5.1 en verde.

---

## FASE 6 — Characterization Package (setup reutilizable) ✅ COMPLETADA (2026-08-26)

Objetivo: medir N líquidos incógnita con un único pase por el asistente. Materializa los
stubs de la welcome (H6) y el "kit persistence" de Plan_FCC S2.2.

### 6.1 Formato del paquete
`*.charpkg` = ZIP:
```
manifest.json      # schema_version, app_version, technique_id, ref_liquid_keys,
                   # temperature_c, sweep (start/stop/points), fuentes por estándar
                   # (measured/imported/preset), timestamps, notas, checksums
open.s1p  short.s1p  ref1.s1p  [ref2.s1p]
[precal_open_ref1.s1p  precal_open_ref2.s1p]      # si hubo pre-cal (Fase 3.1 los persiste)
[dut.s1p  epsilon.csv]                            # opcional: última incógnita + resultado
```
- Módulo nuevo `MC\calibration\characterization_package.py`: `export_package(path, cal,
  session)`, `import_package(path) -> (cal, session_info)`, validaciones (grilla común,
  schema_version, técnica registrada).

### 6.2 Exportar
- Botón "Save characterization package…" en `MeasurementMainWindow` (menú File) y oferta
  al finalizar el wizard. Guarda todo excepto (opcionalmente) la incógnita.

### 6.3 Importar y flujo directo de incógnita
- `characterization_welcome.py::import_characterization_package` (L394–397): file dialog →
  `import_package` → tarjeta-resumen del setup (técnica, líquidos, T, sweep, fechas,
  procedencias) → botón "Measure unknown liquid" que abre el wizard **directo en el paso
  de Incógnita** (pasos previos marcados completos en la sidebar, navegables en solo
  lectura) → Resultados.
- Implementar también los stubs de kits (`_load_characterization_kits`,
  `_on_kit_selection_changed`, `_set_current_kit_selection` L362–381): listar los `.charpkg`
  guardados en `MC\calibration\kits\` para re-uso con un click, sin file dialog.
- Regla de validez temporal: warning si el paquete tiene más de X horas/días (la
  calibración con líquidos caduca rápido — evaporación, temperatura) — configurable.

**Verificación Fase 6**: completar el asistente con `test_data\` → exportar paquete →
cerrar app → importar paquete → medir/importar solo `step6_dut_water_35mm.s1p` →
resultados dan εr′≈78–80 sin repetir pasos.

---

## Mejoras adicionales propuestas (oportunistas, no bloqueantes)

| # | Mejora | Notas |
|---|---|---|
| M1 | ~~Puntos arbitrarios en Step 1~~ — **hecho en 2.8** | ✅ Fase 2 |
| M2 | ~~Import con remuestreo opcional~~ — **hecho**: presets ofrecen remuestreo (2.6) y el import ofrece adoptar el sweep del archivo (2.8) | ✅ Fase 2 |
| M3 | ~~Diagnóstico **Gn(f)** como chequeo de calidad de calibración del método completo: Gn sale solo de los 4 patrones y debe ser suave; picos delatan un patrón malo (típicamente IPA). Mostrar mini-gráfico en Resultados~~ | ✅ completado |
| M4 | ~~Unificar exporters PDF DUT/characterization (hoy clones divergentes)~~ | ✅ completado |
| M5 | ~~Migrar el checkbox `fig.text` picker de "Show indicative reference" a `QCheckBox` real~~ | ✅ completado |
| M6 | ~~About único que respete `Preferences/language`~~ | ✅ completado |
| M7 | ~~Al guardar preset, warning si el líquido del paso ≠ líquido seleccionado en Step 1~~ | ✅ completado |
| M8 | ~~Quitar `logging.basicConfig` side-effect en `SH\utils\dark_light_mode\light_dark_mode.py` L6~~ | ✅ completado |
| M9 | Validación E2E automatizada: test que corre solver completo + simplificado contra `test_data\` y los golden de App_ME2 (`medicion_fluidos\App_ME2\data\measurements\er\*.mat`) | complementa Plan_FCC S2.4 |
| M10 | ~~`_diagnosticar_saltos` (salto relativo >50 % entre puntos → warning de rama) como warning en Resultados~~ | ✅ completado |
| M11 | ~~`steps_manager.update_step_screen` no destruye los widgets de la pantalla anterior: siguen colgando del wizard (se ven N botones "Import" tras N pasos). Fuga leve y fuente de confusión al automatizar; conviene `deleteLater()` al limpiar el layout~~ | ✅ completado |

---

## Orden de implementación y dependencias

```
Fase 1 ✅  →  Fase 2 ✅  →  5.3-bis ✅  →  Fase 3 ✅  →  Fase 4 ✅  →  Fase 5 ✅  →  Fase 6 ✅
```
- **Pendiente**: M9 (Validación E2E automatizada).

## Riesgos

1. **Convención de signos** al portar etanol/metanol y el solver simplificado — mitigar con
   tests vs XLSX NPL y vs `test_data\` (etanol medido).
2. **Cambio de semilla del quíntico** (5.3) puede alterar curvas ya validadas — mantener
   `eps_seed=None` como default hasta validar contra los golden de App_ME2.
3. **Compatibilidad de presets legados** sin sidecar JSON — cubierto en 2.4.
4. **`.charpkg` versionado** — `schema_version` desde el día 1; rechazar versiones futuras.
5. **PDF en QThread**: matplotlib no es thread-safe con backends interactivos — generar los
   PNG en el hilo de UI y solo compilar LaTeX en el worker (o backend `Agg` en el worker,
   patrón de `Sonda_2026_py\gui_funciones.py`).
6. Regla vigente de Plan_FCC: **no tocar archivos fuera de `material_characterization`
   sin aprobación por archivo**. Ya tocados y aprobados en la Fase 1:
   `SH\utils\preferences\{preferences.py, debug_mode.py}`, `SH\utils\export\` (nuevo),
   `DUT\exporters\{latex_exporter.py, export\graph_preview_dialog.py}`,
   `SH\resources\dut_measurement\{en,es}\dut_measurement_features.json`,
   `SH\resources\dut_resource_loader.py`, `.gitignore`.
   Pendientes de OK: `README.md`/`README_ES.md` (4.4) y cualquier refactor de M4.
