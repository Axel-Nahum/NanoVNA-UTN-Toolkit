# Visor de Mediciones — NanoVNA UTN Toolkit

El Visor de Mediciones permite cargar, comparar e inspeccionar archivos de medición Touchstone (`.s1p`, `.s2p`) sin necesidad de realizar una medición en vivo. Está disponible desde los módulos de Medición DUT y Caracterización de Materiales.

---

## Abrir el Visor

- Desde **Medición DUT**: Archivo → Visor de Mediciones  
- Desde **Caracterización de Materiales**: Archivo → Visor de Mediciones  
- Desde el **menú principal**: botón Visor de Mediciones

---

## Cargar Archivos

Hacé clic en **+ Agregar archivos** para seleccionar uno o más archivos `.s1p` o `.s2p`, o en **Agregar carpeta** para cargar todos los archivos compatibles de un directorio.

Los archivos cargados aparecen en el panel izquierdo. El indicador muestra el total de archivos cargados.

---

## Modos de Vista

| Modo | Descripción |
|---|---|
| **Individual** | Muestra un archivo a la vez. Hacé clic en un archivo de la lista para visualizarlo. |
| **Comparar** | Superpone todos los archivos seleccionados en el mismo gráfico para comparación directa. |

---

## Disposición de Gráficos

Seleccioná desde la pestaña **Gráficos** del panel de control:

- **2 gráficos**: una fila — Magnitud arriba, Fase (o Imaginaria) abajo.
- **4 gráficos**: dos columnas — S11 y S21 lado a lado, cada uno con su fila de Magnitud y Fase.

**Parámetro** (solo modo 2 gráficos):
- **S11** — coeficiente de reflexión
- **S21** — coeficiente de transmisión / permitividad (modo caracterización)

**Vista**:
- **Mag + Fase** — Magnitud [dB] y Fase [°]
- **Real + Imag** — Partes Real e Imaginaria

---

## Cursores

Activá hasta dos cursores desde la pestaña **Cursores**.

- Hacé clic en un gráfico para posicionar el cursor activo.
- Arrastrá horizontalmente para moverlo. El cursor se ancla a la frecuencia de dato más cercana (sin interpolación).
- **Vinculado**: cuando está activado, ambos cursores se mueven juntos en todos los gráficos.
- **Δ (C2 − C1)**: muestra la diferencia de frecuencia entre el cursor 2 y el cursor 1.

Las unidades de frecuencia (kHz / MHz / GHz) se seleccionan automáticamente según el valor.

---

## Rango Y

Desde la pestaña **Rango**:

- **Auto**: ajusta el eje Y a todos los datos visibles en cada gráfico de forma independiente.
- **Grilla**: activa/desactiva la grilla por gráfico.
- **Y min / Y max**: establece límites manuales. Dejá ambos vacíos para restaurar el modo automático.

---

## Exportar

Desde la pestaña **Exportar**, elegí DPI y modo de exportación:

| Opción | Resultado |
|---|---|
| **Individual** | Un PNG por gráfico (Mag [dB], Fase [°], Real, Imag). |
| **Pares** | Un PNG por par (Mag + Fase, Real + Imag). |
| **4 gráficos** | Los cuatro gráficos en un único PNG. |

---

## Tema Claro / Oscuro

Hacé clic en el botón **Modo Oscuro 🌙 / Modo Claro 🔆** en el encabezado para cambiar el tema. La ventana se reabre con el nuevo tema aplicado.

El tema es compartido con el resto de la aplicación (se controla desde **Archivo → Preferencias**).

---

## Menú Archivo

| Elemento | Acción |
|---|---|
| Limpiar Selección | Deselecciona todos los archivos de la lista (los gráficos se reinician). |
| Preferencias… | Abre el diálogo de Preferencias de la aplicación. |
| ← Volver | Regresa al módulo que abrió el visor. |

---

## Teclas y Consejos

- El campo de filtro acepta coincidencias parciales sobre el nombre del archivo.
- Los archivos pueden provenir de distintos instrumentos o sesiones; el visor solo lee las columnas de frecuencia y datos.
- Los nombres de archivo para exportar se sugieren en base al nombre del archivo fuente y el tipo de gráfico.

---

## Versión

2.4.0 — Octubre 2026  
UTN FRBA — Proyecto Final
