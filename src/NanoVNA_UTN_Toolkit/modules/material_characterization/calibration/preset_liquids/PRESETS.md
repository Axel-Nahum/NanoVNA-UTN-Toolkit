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

## Presets disponibles (4)

| Preset | Liquido | Rol | Fuente | Barrido | Temp. | Origen |
|---|---|---|---|---|---|---|
| `ipa_r60_probe21mm_18C` | ipa | reference | measured | 1 MHz - 2 GHz / 2000 pts | 18.0 C | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. **Incluido con el toolkit (no se puede borrar ni sobrescribir).** No figura en el archivo de antecedentes (el mas parecido, sonda21-alcisoprop25-06.s1p, difiere en mediana 0.027 de |S11|); fecha de medicion no informada. Planilla entregada por el docente el 2026-10-02: 'Interpolacion medicion S11 IPA sonda 21mm.xlsx'. En la planilla las columnas se rotulan Er'/Er'' pero son Re/Im de S11. Se usan los puntos medidos, no los polinomios de ajuste. Temperatura ~18 C informada por el docente (no registrada con el barrido) |
| `ipa_r60_probe3mm_18C` | ipa | reference | measured | 100 MHz - 6 GHz / 1181 pts | 18.0 C | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. **Incluido con el toolkit (no se puede borrar ni sobrescribir).** Coincide con sonda3-alc-isoprop.s1p del archivo de antecedentes. Planilla entregada por el docente el 2026-10-02: 'Interpolacion medicion S11 IPA sonda 3mm.xlsx'. En la planilla las columnas se rotulan Er'/Er'' pero son Re/Im de S11. Se usan los puntos medidos, no los polinomios de ajuste. Temperatura ~18 C informada por el docente (no registrada con el barrido) |
| `water_r60_probe21mm_18C` | water | reference | measured | 1 MHz - 2 GHz / 2000 pts | 18.0 C | Copper Mountain R60 (S/N 23103002) open-ended coax 21 mm. **Incluido con el toolkit (no se puede borrar ni sobrescribir).** Coincide con 'sonda 21-agua 35mm prof base plastico ancha 06-08.s1p' (35 mm de profundidad, base plastica ancha). Planilla entregada por el docente el 2026-10-02: 'Interpolacion medicion S11 agua sonda 21mm.xlsx'. En la planilla las columnas se rotulan Er'/Er'' pero son Re/Im de S11. Se usan los puntos medidos, no los polinomios de ajuste. Temperatura ~18 C informada por el docente (no registrada con el barrido) |
| `water_r60_probe3mm_18C` | water | reference | measured | 100 MHz - 6 GHz / 1181 pts | 18.0 C | Copper Mountain R60 (S/N 23103002) open-ended coax 3 mm. **Incluido con el toolkit (no se puede borrar ni sobrescribir).** Coincide con sonda3-agua.s1p del archivo de antecedentes. Planilla entregada por el docente el 2026-10-02: 'Interpolacion medicion S11 agua sonda 3mm.xlsx'. En la planilla las columnas se rotulan Er'/Er'' pero son Re/Im de S11. Se usan los puntos medidos, no los polinomios de ajuste. Temperatura ~18 C informada por el docente (no registrada con el barrido) |

<!-- END AUTO-GENERATED TABLE -->

## Presets eliminados

Registro de presets borrados desde el asistente (append-only).
- **2026-08-27T16:04:39** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160158` (water, reference)
- **2026-08-27T16:04:42** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160207` (water, reference)
- **2026-08-27T16:05:44** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160518` (water, reference)
- **2026-08-27T16:05:47** - eliminado `water_open_coax_liquids_simplified_25.0C_50kHz-1.5GHz_101pts_20260827-160522` (water, reference)
- **2026-10-02T23:38:39** - eliminado `ethanol_r60_probe21_2026` (ethanol, reference)
- **2026-10-02T23:38:39** - eliminado `ethanol_r60_probe3_2026` (ethanol, reference)
- **2026-10-02T23:38:39** - eliminado `ipa_r60_probe21_2026` (ipa, reference)
- **2026-10-02T23:38:39** - eliminado `ipa_r60_probe3_2026` (ipa, reference)
- **2026-10-02T23:38:39** - eliminado `open_air_r60_probe21_2026` (air, open)
- **2026-10-02T23:38:39** - eliminado `open_air_r60_probe3_2026` (air, open)
- **2026-10-02T23:38:39** - eliminado `short_r60_probe21_2026` (short, short)
- **2026-10-02T23:38:39** - eliminado `short_r60_probe3_2026` (short, short)
- **2026-10-02T23:38:39** - eliminado `sim_cst2020_alcohol` (ipa, reference)
- **2026-10-02T23:38:39** - eliminado `sim_cst2020_muscle_dut` (muscle, dut)
- **2026-10-02T23:38:39** - eliminado `sim_cst2020_open_air` (air, open)
- **2026-10-02T23:38:39** - eliminado `sim_cst2020_short` (short, short)
- **2026-10-02T23:38:39** - eliminado `sim_cst2020_water` (water, reference)
- **2026-10-02T23:38:39** - eliminado `water_deep35mm_r60_probe21_2026` (water, reference)
- **2026-10-02T23:38:39** - eliminado `water_r60_probe21_2026` (water, reference)
- **2026-10-02T23:38:39** - eliminado `water_r60_probe3_2026` (water, reference)
