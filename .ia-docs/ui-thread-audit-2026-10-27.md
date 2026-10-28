# Auditoría de trabajo pesado en el hilo de UI

Fecha: 2026-10-27. Alcance: `src/NanoVNA_UTN_Toolkit` (unas 60 k líneas, PySide6 6.11, matplotlib Agg).
Origen: el lag del diálogo "Rename liquid" resultó ser un cliente de accesibilidad de
Windows (EoAExperiences.exe), pero la búsqueda dejó dos bugs reales de la app ya
corregidos (timer de tiempo real corriendo con la ventana oculta; filtro de eventos global
de debug). Este documento es la revisión completa que siguió.

## Método

- Cuatro lecturas independientes del código por categoría: timers, E/S bloqueante,
  redibujado de matplotlib y reconstrucción de pantallas, loop de eventos e hilos.
- Verificación propia de los hallazgos de mayor impacto con mediciones headless
  (Qt offscreen, Agg) sobre datos reales de `test_data/sonda21_2026` (201 puntos) y con
  pruebas de comportamiento de PySide6. Las cifras marcadas **medido** son de esas
  pruebas; las demás son estimaciones de lectura.
- Lo que no se midió se marca como estimación. Nada de lo listado se corrigió todavía,
  salvo lo indicado en "Ya corregido".

## Resumen ejecutivo

| # | Problema | Dónde | Costo | Estado |
|---|---|---|---|---|
| 1 | Resultado del worker de medición se procesa en el hilo del worker, no en la UI | `measure_runner.py:299` | crash/corrupción latente | **confirmado** por prueba |
| 2 | Tras cada barrido DUT: 4 `gc.collect()` + 6 redibujados completos | `graphics_update.py`, `cursors_reset.py`, `graphics_refresh_thread.py` | 700 ms por barrido, 360 ms son `gc.collect` | **medido** |
| 3 | Tick de tiempo real DUT redibuja dos figuras completas | `graphic_real_times_update.py:209` | 60–95 ms por tick (90 con Kalman) | **medido** |
| 4 | Loop de tiempo real DUT no se pausa bajo diálogos, ventanas hijas ni minimizado | `real_time.py`, sin `hideEvent` en `graphics_window.py` | todo lo anterior corre debajo del diálogo | confirmado por lectura |
| 5 | Barrido único y tiempo real arrancan juntos y comparten el puerto serie; "Run Sweep" del menú puede lanzar un segundo hilo y abortar la app | `graphics_window.py:462,496`, `graphics_refresh_thread.py:204` | datos cruzados, abort de Qt | confirmado por lectura |
| 6 | Wizard de calibración DUT mide en el hilo de UI con `processEvents` | `sweep_cal.py:249-391` | 0,5–4 s por patrón | confirmado por lectura |
| 7 | Paso de slider de marcador: redibujado completo + escritura INI | `graphics_utils.py:634`, `cursors_visibility.py` | 41 ms por paso | **medido** |
| 8 | Viewer: restaurar desde minimizado borra las curvas | `measurement_viewer.py:2518` | pérdida de estado | **confirmado** por prueba |
| 9 | Viewer: el campo de filtro escanea carpetas recursivamente por tecla | `measurement_viewer.py:1770` | segundos a minutos | confirmado por lectura |
| 10 | Chequeo de LaTeX y render a 300 dpi en el hilo de UI al exportar PDF | `graph_preview_dialog.py:1440`, `pdf_preview_dialog.py:1276` | 1–30 s | confirmado por lectura |

## Hallazgos verificados con medición

Entorno: Qt offscreen, 201 puntos, PC del autor. En pantalla real los tiempos de dibujo
son similares (Agg rasteriza en CPU); el perfilado los infla cerca de 2x.

| Operación | Tiempo |
|---|---|
| `get_settings()` + una lectura | 0,34 ms |
| Construcción de `NanoVNAGraphics` | 470 ms |
| `update_plots_with_new_data` + 2 `draw()` (tras barrido) | 690–720 ms |
| de los cuales `gc.collect()` ×4 | 360 ms |
| de los cuales dibujos completos ×6 | 340 ms |
| `canvas.draw()` de un panel con datos | 22–29 ms |
| Tick de tiempo real, filtro Off | 60–95 ms |
| Tick de tiempo real, Kalman | 82–112 ms |
| Un paso de slider de marcador | 41 ms medio, 86 máx |
| Reconstrucción del paso DUT del wizard de caracterización (rename) | 350 ms |
| Tick de tiempo real de caracterización (solver + chart) | 180–220 ms |

Lectura: el costo de los INI es despreciable (los auditores lo sobreestimaron). Lo que
pesa es el dibujo completo de figuras y los `gc.collect()` explícitos. En el tick de tiempo
real, el perfil muestra dos `draw` completos por tick y el tiempo se va en el layout de
texto de los ejes (ticks y etiquetas), no en los datos.

## Hallazgo crítico de hilos

**`measure_runner.run_s11_sweep_async`** conecta `worker.finished` y `worker.failed` a
closures con `Qt.QueuedConnection`. Prueba directa en PySide6 6.11: un closure sin
receptor QObject corre en el hilo del worker, con o sin `QueuedConnection`. Consecuencia:
`on_success` (que llama `_render`, `setText`, `setEnabled`, y en la ventana de resultados
`compute_epsilon` + `canvas.draw()`) y `QMessageBox.critical` corren fuera del hilo de UI.
Hoy funciona por suerte. Es el mismo problema que el propio repo documenta y resolvió en
`real_time.py` con `_RealtimeController`. Afecta al wizard de caracterización (botón Medir)
y al barrido desde dispositivo de la ventana de resultados.

Fix: un QObject controlador creado en el hilo de UI con slots `on_finished`/`on_failed`,
igual que `_SweepController` en `graphics_refresh_thread.py`.

## Módulo DUT (medición)

### Loop de tiempo real (`shared/utils/real_time`)

- Arranca por defecto 1 s después de abrir la ventana (`graphics_window.py:496`),
  intervalo 100 ms, guarda de solape con `_rt_busy`. Ritmo efectivo = ritmo del
  instrumento, 3–6 barridos/s.
- Por barrido, en el hilo de UI: despike en Python puro (4 pasadas), Kalman punto a punto
  (23 ms a 201 puntos), unas 12 lecturas de INI, actualización de cursores y etiquetas, y
  dos `draw_idle` de figuras completas. **Medido 60–95 ms por tick**, o sea 30–50 % del
  hilo de UI en uso continuo.
- No hay `hideEvent`/`changeEvent`: sigue corriendo minimizado, debajo de todo diálogo
  modal (`sweep_settings_dialog`, `signal_filters`, `set_range`, export, help, etc.) y de
  las ventanas hijas (Sweep Options, View, Edit Graphics).
- `_rt_busy` se libera antes de que el render diferido ocurra; los draws coalescen pero el
  costo de render no se limita.
- Intervalo: `sweep_settings_dialog.py:222` no tiene cota inferior (el módulo de
  caracterización sí clampa a 100 ms).

Fix sugerido, en orden: (a) pausar/reanudar en `hideEvent`/`showEvent` y al abrir
diálogos modales, como ya hace la ventana de resultados de caracterización; (b) mover
despike y Kalman al `SweepWorker.run` (es numpy puro); (c) blitting de la traza y los
cursores con el fondo cacheado tras cada `draw` completo, como ya hace el viewer; (d) no
llamar `set_xlabel`/`set_xlim`/`set_ylim` en cada tick si no cambiaron.

### Barrido único y su post-proceso

- `on_sweep_finished` (`graphics_refresh_thread.py:286-453`) hace en el hilo de UI:
  parseo de 3–7 archivos `.s1p` de calibración con skrf en cada barrido, `rf.Network` del
  DUT, Kalman completo, `update_plots_with_new_data`, reset de marcadores (4 `set_val`
  no silenciosos, cada uno con redibujado e INI), `singleShot(0)` y `singleShot(50)` que
  repiten los cursores y terminan con dos `draw()` síncronos.
- `remove_slider` llama `gc.collect()` (`graphics_utils.py:975`, `2076`), 4 veces por
  barrido: **medido 360 ms**. Es la mitad del congelamiento.
- `panels_utils.py:13-59`: antes del barrido agrega un texto mathtext a cada panel y hace
  `draw()` síncrono, sin quitar el texto anterior.

Fix: quitar los `gc.collect()` (si hacía falta por fugas, resolver la fuga); un solo
`draw` al final; resets de slider con la variante silenciosa; parsear la calibración una
vez y cachearla hasta que cambie.

### Concurrencia en el puerto serie

- `graphics_window.py:462` y `:496`: `run_sweep` y `start_realtime` disparan a los 1000 ms;
  `_trigger` solo mira `_rt_busy`, no el hilo del barrido único. Dos workers intercalan
  comandos en el mismo puerto. En modo tiempo real el botón dice "Reset Kalman" pero sigue
  conectado a `run_sweep` (`graphics_window_body.py:70`).
- `graphics_window.py:389`: la acción de menú "Run Sweep" nunca se deshabilita; una
  segunda llamada sobreescribe `self.thread`/`self.worker` con el hilo anterior vivo →
  "QThread: Destroyed while thread is still running", abort.
- `reconect_button.py:46-51`: `disconnect()`/`connect()` en el hilo de UI sin detener el
  tiempo real; espera el `serial.lock` que el worker tiene durante todo el comando
  (hasta segundos en V2/LiteVNA).
- Si la ventana se cierra antes de 1 s, el `singleShot(1000, start_realtime)` arranca un
  timer huérfano sobre una ventana cerrada (rutas de recrear ventana en
  `calibration_menu.py`, `delete_calibration.py`, `save_calibration.py`, `screens.py`).
- `self.thread = QThread()` en una `QMainWindow` sombrea `QObject.thread()`;
  `real_time.py:108` lee ese atributo y nunca obtiene `None`.

Fix: una sola fuente de verdad del estado del instrumento (ocupado/libre) consultada por
ambos caminos; deshabilitar acción y botón mientras hay barrido; guardar el timer de
arranque y cancelarlo en `closeEvent`; renombrar `self.thread`.

### Wizard de calibración DUT

- `sweep_cal.py:249-391`: `connect`, `setSweep`, `read_frequencies`, `readValues` en el
  hilo de UI; THRU lee `data 1` dos veces (duplicado en 389–391). `processEvents()` en 270
  permite doble click (medición anidada) y Back/Next durante la medición (escribe en
  widgets destruidos). 0,5–4 s de congelamiento por patrón.
- `screens.py:725`: `if step_name == "OPEN" or "SHORT" or "MATCH"` es siempre verdadero;
  se construye un Smith para THRU y se descarta.

Fix: reutilizar `SweepWorker` + controlador de `graphics_refresh_thread.py`; bloquear
navegación durante la medición como hace `measure_runner`.

### Marcadores, diálogos View/Edit, toggles

- Paso de slider: `update_cursor` redibuja la figura completa y escribe
  `Cursor_1_1/index` en el INI en cada movimiento (**41 ms medido**; con marcadores
  enlazados, el doble). El drag con el mouse (`on_motion`, 883–907) llama
  `update_cursor(index)` sin `new_slider` y sale por el `logging.warning` en cada evento.
- Edit Graphics (`edit_graphics_utils.py:325-455`): cada paso de spinbox hace
  `ax.clear()`, nuevo `rf.Network`, `plot_s_smith` y `draw()` síncrono; los color pickers
  dibujan dos veces.
- View (`view_utils.py:164-258`): `toggled` en cada radio → dos llamadas por click, y en la
  rama Smith `setChecked(True)` re-entra `update_graph`.
- Toggle dB/× (`toggle_db_times.py:63`): reconstruye ambos paneles con `gc.collect`, 2
  draws síncronos, 4 cadenas de cursor y un `singleShot(150)` que repite todo.
- Apply en View y Edit recrea ambos paneles aunque cambie uno.
- Figuras `plt.subplots` nunca cerradas en paneles, Edit, View, export y `magnitude_chat_utils`:
  fuga de ~2 figuras por apertura o reconstrucción de ventana.

Fix: blitting de cursores; guardar el índice del marcador al soltar, no por evento;
debounce de spinboxes (100–150 ms); conectar `clicked` en vez de `toggled` o filtrar
`checked`; `plt.close(fig)` o usar `Figure` + `FigureCanvasQTAgg` sin pyplot.

### Exportación PDF (ambos módulos)

- `check_latex_installation()` compila un documento de prueba con `subprocess.run` en el
  hilo de UI (1–5 s; 10–30 s en el primer uso de MiKTeX), redundante porque el diálogo de
  setup ya lo hizo en un hilo. Luego `render_images` a 300 dpi en el hilo de UI (2–5 s).
- Hilos `LaTeXCheckerThread` sin padre: si el diálogo se cierra con Esc/Cancel durante el
  chequeo, el QThread se destruye corriendo (abort). `closeEvent` usa `terminate()` +
  `wait()` sin cota, que puede dejar bloqueos tomados.
- `PdfCompileTask`: X/Esc cierran el diálogo con el hilo vivo (abort).
- Ambos checkers redefinen `finished = Signal(...)`, sombreando `QThread.finished`.

Fix: no repetir el chequeo; renderizar con `Figure` + canvas Agg dentro del worker;
rechazar `reject`/`closeEvent` mientras hay tarea; nunca `terminate()`.

## Módulo de caracterización

- **`measure_runner.py:299-300`**: ver "Hallazgo crítico de hilos".
- Ventana de resultados: `redraw_chart` dibuja dos veces (encola `draw_idle` en
  `_adjust_chart_layout` y luego `draw()` síncrono); `_on_sweep_success_result` suma
  `_upd1`/`_upd2` con escrituras INI y otro `draw_idle`. `compute_epsilon` (90 ms) corre en
  el hilo de UI en cada tick. **Medido 180–220 ms por tick**. Ya se pausa al ocultar.
- Sliders de marcador (`measurement_main_window.py:722-778`): INI + redibujado completo por
  paso (30–80 ms).
- Wizard `_render` (`standard_screen.py:2006-2117`): cada tab, toggle dB/×, checkbox y
  cambio de preset hace `fig.clf()` o `ax.clear()` + `plot_s_smith` + `draw()`; el combo de
  preset recarga desde disco en cada paso de rueda.
- Cada construcción de paso crea un Smith (`create_wizard_smith_chart`, 80–150 ms) que el
  primer `_render` en modo Re/Im descarta con `fig.clf()`.
- Rename y despike (`result_screen.py:650-658`) reconstruyen la pantalla entera
  (**350 ms** medido para rename; 0,3–1 s para despike, que además recalcula ε).
- `result_screen.py:1072` llama `matplotlib.use("Agg")` en un handler: cambia el backend
  global en caliente y cierra las figuras de pyplot.
- `closeEvent` de resultados: `t.quit(); t.wait(1000)` no interrumpe una lectura serie;
  el del wizard no detiene `_active_sweep_thread`.

Fix: controlador de hilo para `measure_runner`; mover `compute_epsilon` al worker; un solo
`draw` por redibujado; actualizar título y etiquetas en lugar de reconstruir el paso;
construir el Smith solo cuando se elige esa pestaña; quitar el `matplotlib.use`.

## Measurement Viewer

- `showEvent` → `_reset_axes()`: **confirmado** que restaurar desde minimizado lo llama y
  borra las curvas mientras los archivos siguen seleccionados. Mover a la construcción o
  guardar con un flag de primera muestra.
- `_apply_filter` por tecla: `Path(text).is_dir()` y, con una carpeta absoluta,
  `_add_folder_to_tree` con `rglob("*")` por subcarpeta en cada nivel. Pegar `C:\` puede
  tardar minutos; una ruta UNC bloquea por tecla. Hacer el escaneo en un worker o solo al
  confirmar con Enter, y usar un recorrido único.
- Cursores C1/C2 y link hacen `_redraw` completo con `tight_layout`; solo cambian los
  artistas de cursor, que ya se blitean en el drag.
- `itemSelectionChanged` redibuja completo por ítem (navegar con flechas o seleccionar
  en bloque multiplica el costo) y parsea el touchstone en el hilo de UI.
- Toggle de tema crea una ventana nueva y pierde la lista de archivos.

## Conexión y otros

- `connection_window.py:652-661`: `wait(5000)` + `terminate()` + `wait(1000)` en
  `closeEvent`; `DeviceWorker` emite `finished` dos veces.
- `connection_window.closeEvent` desconecta el dispositivo que acaba de pasar al menú,
  por eso cada ventana nueva reconecta en el hilo de UI (`graphics_window.py:446-455`,
  `measure_runner.py:203`, `graphics_refresh_thread.py:177`).
- `log_handler.py`: `QTimer.singleShot(0, lambda)` desde hilos de worker; nunca se quita.
  Dormido hoy porque el nivel es INFO.
- Código muerto con `time.sleep` y `processEvents` en `graphics_refresh.py:157-750`,
  todavía importado por `reconect_button.py:9`. Borrar.

## Ya está bien (no tocar)

- `real_time._trigger` + `_RealtimeController`: receptor con afinidad de UI, generación
  para descartar resultados viejos, sin `wait()`.
- `graphics_refresh_thread` con `_SweepController` (salvo el doble arranque).
- `DeviceWorker` en `connection_window`: todo el sondeo en el worker, slots ligados.
- `MeasurementMainWindow`: guarda `_sweep_in_progress` y pausa en `hideEvent`.
- Blitting del drag de cursores en el viewer.

## Plan sugerido por fases

1. **Seguridad de hilos** (corto, alto valor): controlador para `measure_runner`; guardas
   de doble arranque y acción de menú en DUT; cancelar el `singleShot` de arranque en
   `closeEvent`; cierre seguro de los diálogos con hilos de LaTeX/PDF.
2. **Tiempo real DUT**: pausa en `hideEvent`/diálogos; despike y Kalman al worker;
   blitting de traza y cursores; cota inferior del intervalo.
3. **Post-barrido DUT**: quitar `gc.collect()`, un solo `draw`, resets silenciosos,
   calibración cacheada.
4. **Interacción**: marcadores con blitting y guardado al soltar; debounce en spinboxes
   y combos; `clicked` en lugar de `toggled`.
5. **Viewer**: `showEvent`, filtro de carpetas en worker, redibujos parciales.
6. **Caracterización**: solver al worker, un `draw` por redibujado, actualizar en lugar
   de reconstruir, Smith bajo demanda.
7. **Exportación PDF**: render en worker, sin chequeo repetido, sin `terminate()`.

## Ya corregido

Sesión del 2026-10-27, primer commit:

- `measurement_main_window.py`: `hideEvent`/`showEvent` pausan y reanudan el tiempo real.
- `wizard_methods_window.py`: `_FlashDetector` solo con `NANOVNA_DEBUG_FLASH=1` y se
  desinstala en `closeEvent`.

Fase 1, seguridad de hilos (verificada headless con dispositivo simulado):

- `measure_runner.py`: `_CharSweepController` (QObject del hilo de UI) recibe
  `finished`/`failed`/`thread.finished`; `is_sweep_running()` y guarda contra doble
  arranque.
- `graphics_refresh_thread.py`: `oneshot_sweep_running()` (evita el `self.thread` que
  sombrea `QObject.thread()`); `run_sweep` ignora la llamada si ya hay barrido.
- `real_time.py`: `_trigger` no arranca un worker mientras corre el barrido único; el
  helper del botón usa `oneshot_sweep_running`.
- `graphics_window.py`: los timers de arranque son atributos y `closeEvent` los cancela.
- `pdf_generation_task.py`: `PdfCompileTask.on_completed()` entrega en el hilo de UI;
  `detach_checker_thread()` deja terminar solo un checker huérfano, sin `terminate()`.
- `graph_preview_dialog.py`, `pdf_preview_dialog.py`: `reject`/`closeEvent` ignorados
  mientras compila el PDF.
- `latex_export_dialog.py`, `latex_export_setup_dialog.py`: señal `check_done` (ya no
  sombrea `QThread.finished`); `done`/`closeEvent` desacoplan el hilo en vez de matarlo.
