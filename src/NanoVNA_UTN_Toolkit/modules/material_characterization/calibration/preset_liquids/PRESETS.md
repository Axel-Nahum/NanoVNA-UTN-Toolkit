# Presets de medicion - origen y procedencia

Cada preset son dos archivos: `<nombre>.s1p` (Touchstone 1 puerto) y
`<nombre>.json` (metadata). La tabla de abajo se **regenera automaticamente**
desde los sidecars cada vez que se guarda o elimina un preset desde el
asistente: no la edites a mano, edita el `.json` correspondiente.

**Origen del material historico:** los presets de las campanas previas salen de
la carpeta de antecedentes de la sonda,
<https://drive.google.com/drive/folders/1vWChEqFr98Cv9aOmgLwDoIE1WwvhoSyR?usp=drive_link>.

> **Advertencia.** En esa carpeta, la mayoria de los `.s1p` de las campanas
> **UTN 2021 y UTN 2024** NO contienen S11: contienen la **permitividad ya
> calculada** guardada con extension `.s1p`. Nunca importarlos como mediciones.
> Los unicos S11 validos verificados son los de 2026 (Copper Mountain R60), las
> simulaciones CST 2020 y los sets NanoVNA de App_ME2 / Kupce 2024.

<!-- BEGIN AUTO-GENERATED TABLE - do not edit by hand -->

## Presets disponibles (16)

| Preset | Liquido | Rol | Fuente | Barrido | Temp. | Origen |
|---|---|---|---|---|---|---|
| `ethanol_r60_probe21_2026` | ethanol | reference | measured | 1 MHz - 2 GHz / 2000 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. Alcohol etilico. Antecedentes de la sonda (Drive UTN). Archivo original: sonda21-alc-etilico25-06.s1p |
| `ethanol_r60_probe3_2026` | ethanol | reference | measured | 100 MHz - 6 GHz / 1181 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. Alcohol etilico. Antecedentes de la sonda (Drive UTN). Archivo original: sonda3-alc-etilico.s1p |
| `ipa_r60_probe21_2026` | ipa | reference | measured | 1 MHz - 2 GHz / 2000 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. Alcohol isopropilico (propan-2-ol). Antecedentes de la sonda (Drive UTN). Archivo original: sonda21-alcisoprop25-06.s1p |
| `ipa_r60_probe3_2026` | ipa | reference | measured | 100 MHz - 6 GHz / 1181 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. Alcohol isopropilico (propan-2-ol). Antecedentes de la sonda (Drive UTN). Archivo original: sonda3-alc-isoprop.s1p |
| `open_air_r60_probe21_2026` | air | open | measured | 1 MHz - 2 GHz / 2000 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. Sonda al aire (patron OPEN). Antecedentes de la sonda (Drive UTN). Archivo original: sonda21-aire.s1p |
| `open_air_r60_probe3_2026` | air | open | measured | 100 MHz - 6 GHz / 1181 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. Sonda al aire (patron OPEN). Antecedentes de la sonda (Drive UTN). Archivo original: sonda3-aire.s1p |
| `short_r60_probe21_2026` | short | short | measured | 1 MHz - 2 GHz / 2000 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. Sonda cortocircuitada. Antecedentes de la sonda (Drive UTN). Archivo original: sonda21-short.s1p |
| `short_r60_probe3_2026` | short | short | measured | 100 MHz - 6 GHz / 1181 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. Sonda cortocircuitada. Antecedentes de la sonda (Drive UTN). Archivo original: sonda3-short.s1p |
| `sim_cst2020_alcohol` | ipa | reference | simulated | 100 MHz - 10 GHz / 100 pts | - | CST Studio Suite (simulacion) open-ended coax (modelo CST). Alcohol simulado. Reconstruido de modS11alcohol / phaseS11alcohol en ws_patrones_2020.mat (magnitud lineal + fase en grados, igual que pol2complex.m). El |S11| de origen supera levemente 1 en algunos puntos: es un artefacto del post-proceso de CST, no un error de conversion. Antecedentes de la sonda (Drive UTN). NO es una medicion |
| `sim_cst2020_muscle_dut` | muscle | dut | simulated | 100 MHz - 10 GHz / 100 pts | - | CST Studio Suite (simulacion) open-ended coax (modelo CST). Musculo sin capa de aceite; el .mat trae Er_musculo_real / Er_musculo_tgD como valor teorico esperado. Reconstruido de modS11musculoaceite000 / phaseS11musculoaceite000 en ws_patrones_2020.mat (magnitud lineal + fase en grados, igual que pol2complex.m). El |S11| de origen supera levemente 1 en algunos puntos: es un artefacto del post-proceso de CST, no un error de conversion. Antecedentes de la sonda (Drive UTN). NO es una medicion |
| `sim_cst2020_open_air` | air | open | simulated | 100 MHz - 10 GHz / 100 pts | - | CST Studio Suite (simulacion) open-ended coax (modelo CST). Patron OPEN simulado. Reconstruido de modS11open / phaseS11open en ws_patrones_2020.mat (magnitud lineal + fase en grados, igual que pol2complex.m). El |S11| de origen supera levemente 1 en algunos puntos: es un artefacto del post-proceso de CST, no un error de conversion. Antecedentes de la sonda (Drive UTN). NO es una medicion |
| `sim_cst2020_short` | short | short | simulated | 100 MHz - 10 GHz / 100 pts | - | CST Studio Suite (simulacion) open-ended coax (modelo CST). Patron SHORT simulado. Reconstruido de modS11short / phaseS11short en ws_patrones_2020.mat (magnitud lineal + fase en grados, igual que pol2complex.m). El |S11| de origen supera levemente 1 en algunos puntos: es un artefacto del post-proceso de CST, no un error de conversion. Antecedentes de la sonda (Drive UTN). NO es una medicion |
| `sim_cst2020_water` | water | reference | simulated | 100 MHz - 10 GHz / 100 pts | - | CST Studio Suite (simulacion) open-ended coax (modelo CST). Agua simulada. Reconstruido de modS11agua / phaseS11agua en ws_patrones_2020.mat (magnitud lineal + fase en grados, igual que pol2complex.m). El |S11| de origen supera levemente 1 en algunos puntos: es un artefacto del post-proceso de CST, no un error de conversion. Antecedentes de la sonda (Drive UTN). NO es una medicion |
| `water_deep35mm_r60_probe21_2026` | water | reference | measured | 1 MHz - 2 GHz / 2000 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. Agua a 35 mm de profundidad, base plastica ancha. Antecedentes de la sonda (Drive UTN). Archivo original: sonda 21-agua 35mm prof base plastico ancha 06-08.s1p |
| `water_r60_probe21_2026` | water | reference | measured | 1 MHz - 2 GHz / 2000 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. Agua destilada. Antecedentes de la sonda (Drive UTN). Archivo original: sonda21-agua25-06.s1p |
| `water_r60_probe3_2026` | water | reference | measured | 100 MHz - 6 GHz / 1181 pts | - | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. Agua destilada. Antecedentes de la sonda (Drive UTN). Archivo original: sonda3-agua.s1p |

<!-- END AUTO-GENERATED TABLE -->

## Presets eliminados

Registro de presets borrados desde el asistente (append-only).
- **2026-08-27T16:04:39** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160158` (water, reference)
- **2026-08-27T16:04:42** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160207` (water, reference)
- **2026-08-27T16:05:44** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160518` (water, reference)
- **2026-08-27T16:05:47** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160522` (water, reference)
