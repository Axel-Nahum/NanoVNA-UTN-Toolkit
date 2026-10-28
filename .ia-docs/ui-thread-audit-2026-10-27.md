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

Fase 2, tiempo real del DUT (2026-10-28, verificada headless):

- `updates/blit_manager.py` (nuevo): `RealtimeBlitter`, receta BlitManager de matplotlib.
  Traza y cursores van `animated`; tras cada dibujo completo se captura el fondo y se
  pintan encima; el tick restaura el fondo, dibuja los artistas y hace `blit`.
- `graphic_real_times_update.py`: el tick usa los blitters; `set_xlabel`/`set_xlim`/
  `set_ylim` solo cuando cambian; autoescalado con histéresis (mantiene límites mientras
  los datos entren y usen al menos el 60 % del rango). **Medido: tick de 85 ms a 9–14 ms**,
  un dibujo completo al inicio y otro solo cuando cambian los límites.
- `cursor_real_time_update.py`: `draw=False` deja el dibujo al blitter.
- `real_time.py`: despike y suavizado pasan al `SweepWorker` (señal con 5 objetos);
  solo Kalman queda en `_done`; `pause_realtime`/`resume_realtime`; `stop_realtime` y el
  toggle liberan los blitters; `RT_MIN_INTERVAL_MS = 100`.
- `graphics_window.py`: `event` (WindowBlocked/Unblocked), `changeEvent` (minimizar),
  `hideEvent`/`showEvent` pausan y reanudan el loop.
- `graphics_utils.py`: `_pin_info_panel` fija la altura e ignora el ancho de los paneles
  de información; sin eso cada cambio de texto redimensionaba el canvas (resizeEvent +
  redibujado completo por tick), un costo que ya existía antes del blitting.
- `sweep_settings_dialog.py`: intervalo acotado a `RT_MIN_INTERVAL_MS`.
- Pendiente de esta fase: Kalman sigue en el hilo de UI (23 ms a 201 puntos) porque su
  estado vive en la ventana y se resetea desde la UI; moverlo requiere reemplazar los
  objetos de filtro en lugar de mutarlos.

Fase 3, post-barrido del DUT (2026-10-28, verificada headless):

- `calibration/touchstone_cache.py` (nuevo): `load_network`/`load_s` cachean los
  archivos de términos de error por ruta + mtime + tamaño; los usan `methods.py`,
  `kits.py`, el DUT importado en `graphics_refresh_thread.py` y el worker de
  `real_time.py`. Un archivo reescrito al recalibrar se vuelve a leer solo; las vistas
  son de solo lectura. (El parseo medía 4 ms por barrido, menos de lo estimado en el
  hallazgo; se cachea igual porque corre también en cada tick de tiempo real.)
- `graphics_utils.py`: sin `gc.collect()` en `remove_slider` (×2). **Medido: 360 ms
  por barrido.**
- `graphics_update.py`: `update_plots_with_new_data(draw=False)` deja el dibujo al
  llamador.
- `graphics_refresh_thread.py`: `on_sweep_finished` reconstruye, posiciona los
  marcadores y encola un `draw_idle` por panel; sin los `update_cursor` repetidos ni el
  `singleShot(50)` con dos `draw()` síncronos.
- `cursors_reset.py`: `_reset_markers_after_sweep` reescrita: rango y valor de los 4
  sliders en silencio, 4 actualizadores de cursor, sin dibujos ni `singleShot(0)`. La
  versión anterior consultaba `cursor.ax` (el atributo es `axes`) y retornaba al inicio:
  era un no-op, y el estado final lo dejaban las llamadas repetidas del handler.
- `sliders_reset.py`: resets antes del barrido y tras reconectar con el setter
  silencioso; tras reconectar `draw_idle` en vez de `draw`.
- `panels_utils.py`: el mensaje de espera reemplaza al anterior (por `gid`) en vez de
  acumularse, y encola el dibujo con `draw_idle`.
- `set_slider_val_silent.py`: corregido un bug latente. Reconectaba los observers con
  `on_changed(ref)` sobre los wrappers de referencia del registry de matplotlib, y todo
  movimiento posterior del slider fallaba con `TypeError` (afectaba al tiempo real cuando
  cambiaba la cantidad de puntos). Ahora apaga `slider.eventson` alrededor de `set_val`.
- **Medido por barrido (hilo de UI, 201 puntos): 840 ms → 215–235 ms.** Dibujos
  completos por panel 6 → 2 (mensaje de espera y resultado); `gc.collect` 4 → 0;
  parseos de calibración por barrido 1 → 0. Estado final idéntico al anterior (sliders en
  0 con rango 0..n-1, cursores visibles en el índice 0, paneles de información llenos).
- Lo que queda (~90 ms): `ax.clear()` y reconstrucción de ejes, sliders (4 `add_axes` +
  4 `Slider`) y cursores en cada barrido dentro de `update_plots_with_new_data`.
  Actualizar en lugar de reconstruir es tema de la fase 4 (marcadores).

Fase 4, interacción (2026-10-28, verificada headless):

- `shared/utils/real_time/updates/marker_interaction.py` (nuevo): un movimiento de
  marcador cambia solo los dos cursores y la barra y manija del slider; esos artistas
  se pintan por blitting con el mismo `RealtimeBlitter` de la fase 2, compartiendo el
  registro `_rt_blitters` y el conjunto de artistas con el tick de tiempo real, así un
  slider durante tiempo real no invalida el fondo del tick ni al revés. Las varias
  llamadas por evento (callback del slider, wrapper, etiquetas) se juntan en un blit por
  pasada del loop; si ya hay un dibujo completo encolado o `figure.stale` es falso, no
  pinta nada. `slider.drawon = False`, porque el blit repinta la manija.
  **Medido: paso de slider de 37 ms (un dibujo completo) a 11 ms (cero).**
- Índice del marcador (`Cursor_x_y/index`): guardado una vez por ráfaga (250 ms) en
  lugar de 1,4 ms de escritura de INI por evento; `flush_marker_indices` antes de que lo
  lean Edit Graphics, la diferencia de frecuencias y al cerrar la ventana.
- `graphics_utils.py`: los cuatro `update_cursor` piden el blit en vez de `draw_idle` y
  difieren el guardado; `on_pick`/`on_motion` comparan contra los cursores y sliders
  **actuales** de la ventana y mueven el slider (`set_val`), que dispara toda la cadena.
  El arrastre con el mouse estaba muerto desde el primer barrido: el handler comparaba
  contra el artista original, reemplazado en cada barrido, y los cursores nuevos no
  tenían `picker`. `enable_cursor_picking` (en `cursors_update.py`) lo repone tras cada
  recreación, también en el Apply de Edit Graphics.
- `cursors_visibility.py`: los cuatro wrappers piden el blit en vez de `draw_idle`.
- `toggle_db_times.py`: reconstrucción con `draw=False`, `_reset_markers_after_sweep` y
  un `draw_idle` por panel. **Medido: 1 dibujo por panel** en vez de 2 síncronos más los
  del reset de sliders y un `singleShot(150)` que repetía todo.
- `view_utils.py`: `update_graph(checked=True)` con guarda de reentrada; `toggled` solo
  redibuja para el botón que queda marcado, y la rama Smith fija S11 sin reentrar.
  **Medido: 1 dibujo por click** (antes 2, y 3 en Smith).
- `edit_graphics_utils.py`: spinboxes con debounce de 120 ms (`QTimer` single-shot):
  una ráfaga de 5 pasos reconstruye la vista previa una vez; los color pickers ya no
  dibujan dos veces.
- Figuras de paneles, View y Edit creadas con `Figure` + `add_subplot` en vez de
  `plt.subplots`: pyplot las registraba en `Gcf` y nunca se cerraban (fuga de 2 figuras
  por ventana o reconstrucción). Verificado: `plt.get_fignums()` no crece.
- Pendiente de esta fase: Apply de View/Edit y el toggle dB/× siguen reconstruyendo
  los dos paneles aunque cambie uno; la reconstrucción de sliders por barrido (~90 ms)
  sigue en `update_data_references`. Separar `update_plots_with_new_data` por panel.

Fase 5, Measurement Viewer (2026-10-28, verificada headless; todo en
`shared/measurement_viewer/measurement_viewer.py`):

- `showEvent`: solo la primera vez hace el layout (`_redraw` de la selección actual).
  Restaurar desde minimizado llamaba `_reset_axes()` y borraba las curvas con los
  archivos aún seleccionados. **Verificado: 52 líneas antes y después de restaurar.**
- Parseo de Touchstone en un worker (`_BackgroundWorker` en un `QThread` sin padre,
  resultado entregado a un método de la ventana, es decir en el hilo de UI). El costo real
  no era el parseo (2 ms por archivo) sino el `import` del parser en la primera selección:
  **1,26 s medidos en el hilo de UI**. Ahora la llamada de selección tarda 3 ms y la curva
  aparece ~240 ms después; el cursor del árbol muestra "ocupado" mientras tanto.
- `itemSelectionChanged` con debounce de 40 ms (`_selection_timer`): navegar con flechas o
  seleccionar en bloque redibuja una vez por ráfaga. **Medido: 5 selecciones, 1 dibujo
  (antes 5 dibujos, 1,1 s).**
- Escaneo de carpetas en el worker con un solo `os.walk` bottom-up (`_scan_folder_tree`)
  en lugar de un `rglob` por subcarpeta y nivel; la caja de filtro agrega la carpeta solo
  con Enter (`_filter_submitted`), tipear solo filtra por nombre (antes `is_dir` y escaneo
  por tecla). **Medido: llamada de 4–7 ms en el hilo de UI (antes 53 ms test_data, 290 ms
  el árbol de src); el árbol aparece ~50 ms después.** Badge "Scanning…" mientras corre.
- Cursores C1/C2 y enlace: solo se recrean los artistas de cursor y se blitean sobre el
  fondo guardado; antes `_redraw` completo con `tight_layout`. **Medido: 280 ms → 11–14 ms,
  cero dibujos completos.** `_draw_cursors` ya no toma otros cursores (animados) como
  líneas de datos. Colocar el primer cursor con click tampoco redibuja.
- `draw_event` hook (`_on_draw_event`): cada dibujo completo, incluido el de Qt tras un
  resize o cualquier `draw_idle`, recaptura el fondo y pinta los cursores. Antes un
  resize dejaba los cursores invisibles hasta el siguiente `_redraw`.
- `closeEvent`: los hilos en curso se desconectan y se dejan terminar solos
  (`_detached_threads`), nunca `terminate()`.
- Toggle de tema: la ventana nueva recibe la lista de archivos, los datos parseados, los
  colores y la selección (`_transfer_files_to`); las carpetas se reescanean en el worker y
  la selección se aplica al llegar (`_pending_select`).
- Sin cambios: cambio de grilla (125 ms) y de layout 2/4 (460 ms) siguen siendo un dibujo
  completo, porque cambia el fondo.

Fase 6, caracterización (2026-10-28, verificada headless con calibración real de
`tests/data`, set 21 mm, 201 puntos):

- `shared/utils/background_task.py` (nuevo): `run_in_background(fn, args, on_done,
  registry)` y `detach_background_threads(registry)`, el patrón de la fase 5 extraído del
  visor (que ahora lo importa): hilo sin padre, resultado a un método ligado de la ventana,
  al cerrar se desconecta y se deja terminar.
- `measure_runner.py`: `run_s11_sweep_async(..., post_process=None)` ejecuta el solver en
  el mismo worker del barrido; `detach_active_sweep(wizard)` para cerrar el wizard con un
  barrido en curso (antes el QThread quedaba referenciado por la ventana destruida).
- `measurement_main_window.py` (resultados): el tick de tiempo real pasa
  `cal.compute_epsilon` como `post_process`, y el modo archivo parsea y resuelve en
  `_file_sweep_compute` en segundo plano. **Medido: el solver cuesta 450–680 ms en este set
  (el informe estimaba 90 ms); el tick en el hilo de UI baja de 615 ms a 80–110 ms, con un
  dibujo en lugar de dos** (`_adjust_chart_layout(draw=False)`, `_upd1/_upd2(draw=False)`).
  Marcadores: cursores y manijas blitados con `RealtimeBlitter` (`drawon=False`), INI por
  ráfaga (`_save_ini_later`, 250 ms, flush al cerrar). **Medido: paso de slider 44 → 2–5 ms,
  cero dibujos; barrido desde archivo 914 ms bloqueando → 3 ms.** `closeEvent` sin
  `quit()+wait(1000)`.
- `epsilon_chart.py`: `axes.formatter.use_mathtext` dejaba de ser global. Estaba en
  `plt.rcParams` y convertía en mathtext **todas** las etiquetas de ticks de la app en
  cuanto se importaba el módulo; cada etiqueta nueva cuesta ~14 ms de parseo (fuente CM) y
  el caché de matplotlib guarda 50. **Medido: el primer dibujo de un paso del wizard
  gastaba 450 ms en etiquetas de ticks.** Ahora `_use_cm_ticks(ax)` lo activa solo en el
  gráfico de ε (el que lo pedía) y el caché del parser se amplía a 512 entradas.
- `standard_screen.py`: Smith bajo demanda (`create_wizard_chart_canvas` en
  `smith_chart_utils.py`: figura y canvas sin grilla; `_render` la dibuja al elegir la
  pestaña); `_render` con `draw_idle` (el primer resize del canvas ya encola un dibujo);
  combo de presets con debounce de 150 ms. **Medido: reconstrucción del paso DUT (camino del
  rename) ~450–570 ms → 230–320 ms.** El rename sigue reconstruyendo el paso: del nombre
  dependen título, instrucción, sidebar, leyenda y la lista de presets del líquido, y una
  actualización parcial era más riesgosa que la reconstrucción ya barata.
- `result_screen.py`: sin `matplotlib.use("Agg")` ni `plt.subplots` en el popup de Gn
  (`Figure` directo); el toggle de despike recalcula ε en segundo plano
  (`wizard._on_despike_recomputed`, en `wizard_methods_window.py`) y recién entonces
  reconstruye la pantalla; `closeEvent` del wizard desacopla barrido y recomputes.
- Pendiente de esta fase: `update_epsilon_curves` sigue haciendo `ax.clear()` + replot por
  tick (~70 ms del tick actual); actualizar las dos líneas en sitio con histéresis de
  límites como en el DUT (fase 2) lo bajaría a blitting puro.

Fase 7, exportación PDF (2026-10-28, verificada headless con MiKTeX real, ambos
módulos):

- `shared/utils/export/latex_check.py` (nuevo): el compilador que ya compiló el documento
  de prueba en este proceso se recuerda; `_test_latex_compiler` de los dos exportadores lo
  consulta antes de compilar y lo registra al pasar. El diálogo de setup ya hacía la
  prueba en un hilo; la vista previa la repetía en el hilo de UI justo antes de exportar.
  **Medido: 590–1100 ms la primera vez, 0,01 ms después, compartido entre DUT y
  caracterización.** Los fallos no se recuerdan (instalar LaTeX a mitad de sesión se
  detecta en el chequeo siguiente).
- `shared/utils/export/agg_figure.py` (nuevo): `new_agg_figure` = `Figure` +
  `FigureCanvasAgg`, sin pyplot ni Qt. Reemplaza `plt.subplots` en los gráficos de
  respaldo (`_generate_plots` ×5 y ×2), en los gráficos de calibración del reporte DUT
  (`_cal_emit_plots`, ×3) y en los de pasos de caracterización (`_render_step_charts`).
  Los de calibración **ya corrían en el worker de compilación con pyplot y backend QtAgg**:
  `plt.subplots` crea un canvas y una ventana Qt desde un hilo que no es el de UI.
- `graph_preview_dialog.py`, `pdf_preview_dialog.py`: la figura de vista previa es una
  `Figure` plana con su `FigureCanvasQTAgg`, no `plt.subplots`. Sus copias profundas
  (`saved_figures`) dejan de arrastrar un manager de pyplot (cada copia registraba una
  ventana QtAgg oculta: fuga por cada página navegada) y quedan con `FigureCanvasBase`, así
  `savefig` es Agg puro y seguro fuera del hilo de UI. `_generate_pdf` manda al
  `PdfCompileTask` el chequeo, el render a 300 dpi y la compilación; el hilo de UI solo
  pone el botón en "Generating…" y muestra el resultado. **Medido: el click de Export
  vuelve en 14–16 ms (antes chequeo 1–5 s + render 2–5 s bloqueando); el PDF se escribe
  igual, sin segunda compilación de prueba.** Un error del chequeo llega por el mismo
  `_on_done` (mensaje "LaTeX installation error…").
- Verificado además: sin figuras de pyplot ni widgets Qt creados durante el render en el
  worker (`plt.get_fignums()` y `QApplication.allWidgets()` estables).

Con esto quedan aplicadas las siete fases del plan. Lo que sigue pendiente está anotado en
cada fase: Kalman del DUT en el hilo de UI (fase 2), reconstrucción de sliders por barrido
(fase 3), Apply de View/Edit sobre ambos paneles (fase 4), y `ax.clear()` por tick en el
gráfico de ε (fase 6).
