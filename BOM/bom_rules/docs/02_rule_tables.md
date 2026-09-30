# Rule Tables

Status: Sprint 1 static knowledge tables.

Each table row must be tagged as one of:

- `hard_constraint`: validation must reject violations.
- `default_preference`: deterministic rule engine can use this when customer did not specify.
- `fallback_heuristic`: allowed only when primary evidence is missing.

## Source Inputs Used

- Corrected 559-record JSON/CSV dataset.
- `bom_system/bom_engine.py` prototype formulas.
- `BAG_TYPE_-_UPANEL..pdf` U-panel formulas.
- Scanned work-order notes from `DocScanner 13 Apr 2026 ...pdf`.
- Bag-type taxonomy from `U_Panel_Bag_=_Upanel_Bug.pdf`.
- GSM and belt GPM tables from the supplied images.

## 1. Canonical Components

Allowed canonical component names:

- BODY PANEL
- SIDE PANEL
- BOTTOM PANEL
- TOP PANEL
- TOP FLAP
- SKIRT
- FILLING SPOUT
- DISCHARGE SPOUT
- BAFFLE
- DS FLAP
- DS PATCH
- LINER
- CORNER LOOP
- FULL BODY LOOP
- STEVEDORE LOOP
- FS TIE
- DS TIE
- PETAL TIE
- TUCKING TIE
- DDP
- DOC POCKET
- LOOP PROTECTOR
- TOP BAND
- BELLY BAND
- TABBING
- STITCHING
- PRINTING
- LABEL

Rule level: `hard_constraint`.

## 2. Loom Width Table

Initial allowed loom widths from the corrected dataset and prototype:

`[35, 40, 45, 47, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 63, 64, 65, 67, 68, 70, 72, 73, 74, 75, 77, 78, 80, 81, 82, 83, 84, 85, 87, 88, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 125, 127, 128, 129, 133, 136, 140, 144, 150, 160, 165, 169, 170, 176, 180, 190, 192, 194, 195, 196, 200, 204, 214, 224, 255]`

Rule level: `hard_constraint`.

Open review item: decide whether to restrict to production loom widths only, or
allow all observed component widths. The validation gate must support either
table version.

## 3. GSM vs SWL/SF Table

### Square Corner, SF 5:1

| SWL kg | body/bottom GSM |
|---|---:|
| <=250 | 70 |
| 251-500 | 110 |
| 501-750 | 120 |
| 751-1100 | 130 |
| 1101-1250 | 140 |
| 1251-1500 | 160 |
| 1501-1600 | 180 |
| 1601-1700 | 200 |
| 1701-1800 | 220 |
| 1801-1900 | 230 |
| 1901-2000 | 240 |

### Square Corner, SF 6:1/UN

| SWL kg | body/bottom GSM |
|---|---:|
| <=250 | 110 |
| 251-500 | 130 |
| 501-750 | 130 |
| 751-1100 | 140 |
| 1101-1250 | 160 |
| 1251-1500 | 180 |
| 1501-1600 | 220 |
| 1601-1800 | 240 |

### Cross Corner, SF 5:1

| SWL kg | body/bottom GSM |
|---|---:|
| <=250 | 130 |
| 251-500 | 130 |
| 501-750 | 140 |
| 751-1100 | 155 |
| 1101-1250 | 165 |
| 1251-1500 | 170 |
| 1501-1600 | 180 |
| 1601-1700 | 200 |
| 1701-1800 | 220 |
| 1801-1900 | 230 |
| 1901-2000 | 240 |

### Cross Corner, SF 6:1/UN

| SWL kg | body/bottom GSM |
|---|---:|
| <=250 | 110 |
| 251-500 | 130 |
| 501-750 | 130 |
| 751-1100 | 140 |
| 1101-1250 | 160 |
| 1251-1500 | 180 |
| 1501-1600 | 220 |
| 1601-1800 | 240 |

Rule level: `hard_constraint` for minimum GSM. The rule engine may choose a
higher GSM based on retrieval/customer pattern, but validation must reject lower
than this threshold.

## 4. Circular Fabric GSM for 1/2 Loop Bags

### SF 5:1

| SWL kg | body GSM | bottom GSM |
|---|---:|---:|
| <=600 | 90 | 130 |
| 601-700 | 100 | 130 |
| 701-800 | 110 | 140 |
| 801-1000 | 140 | 160 |
| 1001-1250 | 150 | 170 |
| 1251-1500 | 190 | 230 |

### SF 6:1

| SWL kg | body GSM | bottom GSM |
|---|---:|---:|
| <=600 | 100 | 130 |
| 601-700 | 110 | 130 |
| 701-800 | 120 | 140 |
| 801-1000 | 140 | 160 |
| 1001-1250 | 160 | 180 |
| 1251-1500 | 220 | 250 |

Rule level: `hard_constraint` for minimum GSM.

## 5. Pope Pack GSM Table

| POPE | height <120 | height 120-180 | height >180 |
|---:|---:|---:|---:|
| 1000 | 180 | 170 | 160 |
| 1200 | 200 | 180 | 170 |
| 1500 | 220 | 200 | 180 |

Rule level: `fallback_heuristic` until validated against more historical BOMs.

## 6. Belt GPM / Width Table

### Corner Loop, SF 5:1

| SWL kg | g/m | width mm |
|---|---:|---:|
| <=500 | 25 | 40 |
| 501-1000 | 30 | 40 |
| 1001-1250 | 35 | 50 |
| 1251-1500 | 35 | 50 |
| 1501-2000 | 50 | 50 |

### Corner Loop, SF 6:1/UN

| SWL kg | g/m | width mm |
|---|---:|---:|
| <=500 | 30 | 40 |
| 501-750 | 35 | 40 |
| 751-1000 | 35 | 40 |
| 1001-1250 | 45 | 50 |
| 1251-1500 | 45 | 50 |
| 1501-2000 | 50 | 50 |

### Cross Corner, SF 5:1

| SWL kg | g/m | width mm |
|---|---:|---:|
| <=500 | 30 | 50 |
| 501-750 | 45 | 75 |
| 751-1000 | 45 | 75 |
| 1001-1250 | 50 | 75 |
| 1251-1500 | 50 | 75 |
| 1501-2000 | 60 | 80 |

### Cross Corner, SF 6:1/UN

| SWL kg | g/m | width mm |
|---|---:|---:|
| 501-750 | 45 | 75 |
| 751-1000 | 50 | 75 |
| 1001-1500 | 50 | 75 |
| 1501-2000 | 60 | 80 |

Rule level: `default_preference`. Validation permits values observed in dataset
if they exceed minimum load suitability.

## 7. U-Panel Geometry Rules

From `BAG_TYPE_-_UPANEL..pdf` and scanned notes:

- Body panel width: external width + 8 cm, then nearest allowed loom width.
- Body panel cut: `2 * external_H + external_L + 10`.
- Side panel width: external width + 8 cm.
- Side panel cut: external height + 8 cm.
- Top panel: `(external_L + 8) x (external_W + 8)`.
- Filling spout fabric width: spout height + 5 cm.
- Filling spout cut: `diameter * 3.14 + 12`.
- Discharge spout height with iris: `spout_h + 5 + diameter/2 + 7`.
- Discharge spout cut: `diameter * 3.14 + 12`.
- FS/DS tie: 125 cm, usually 2 pieces, 6 g/m or 7 g/m.
- Iris tie: `diameter * 3.14 + 38`.
- U-panel belt cut: `LL + SL + 50` or handwritten standard `25 + 25 + 40 + 85 = 175 cm`.
- DDP: 4.5 g/m, length from seam/spout path, doubled for double dust proof.
- Doc pocket: 75 micron LDPE, A4/11x18 inch variants use LDPE density factor.
- Stitching rough rule in notes: about `0.45 * bag_height`.

Rule level: geometry formulas are `hard_constraint` for rule-engine draft, with
retrieval allowed to override only by selecting a historically observed component
dimension that still passes physics.

## 8. Bag Type Classification Rules

From scanned taxonomy:

| Raw phrase | canonical bag_type | notes |
|---|---|---|
| U panel, U pannel, U+2 | u_panel | corner loop, belt width 25-55mm |
| Circular, tubular fabric | circular | cross corner loop, belt width 70-100mm |
| 4 panel baffle, Q bag, anti bulge | four_panel_baffle | corner/cross-corner variants |
| 4 panel | four_panel | no baffle unless specified |
| Single loop | single_loop | loop free height often given |
| Double loop, two loop | two_loop | two loop family |
| Two panel, C-type | two_panel | includes conductive type C variants |
| Tubular bag | circular or tubular | only two dimensions may be given |
| Omega bag | omega | top stitching three times in double row |
| Platen bag | platen | requires explicit platen mention |
| Box bag | box | requires explicit box mention |
| Tunnel bag | tunnel | tunnel height mentioned with bag size |
| Container bag | container | long liner/container length, 5m-12m |
| Conductive bag | conductive | Type C bag with conductive yarn |

Rule level: `default_preference`, but explicit customer text wins.

## 9. Mandatory Component Matrix

| bag_type | mandatory components |
|---|---|
| u_panel | BODY PANEL, SIDE PANEL, CORNER LOOP, STITCHING, LABEL |
| circular | BODY PANEL, BOTTOM PANEL, CORNER LOOP, STITCHING, LABEL |
| four_panel | BODY PANEL, BOTTOM PANEL, TOP/BOTTOM per spec, CORNER LOOP, STITCHING, LABEL |
| four_panel_baffle | BODY PANEL, BOTTOM PANEL, BAFFLE, CORNER LOOP, STITCHING, LABEL |
| two_panel | BODY PANEL, BOTTOM PANEL or SIDE PANEL, STITCHING, LABEL |
| single_loop | BODY PANEL, BOTTOM PANEL, FULL BODY LOOP or loop family, STITCHING, LABEL |
| two_loop | BODY PANEL, BOTTOM PANEL, FULL BODY LOOP or two-loop family, STITCHING, LABEL |

Optional components are driven by `StructuredSpec`: TOP PANEL, SKIRT, TOP FLAP,
FILLING SPOUT, DISCHARGE SPOUT, DS FLAP, DS PATCH, FS TIE, DS TIE, PETAL TIE,
TUCKING TIE, LINER, DDP, DOC POCKET, LOOP PROTECTOR, STEVEDORE LOOP, PRINTING.

Rule level: mandatory matrix is `hard_constraint`.

## 10. Weight Formula Rules

Fabric:

`weight_g = gsm_area * width_cm * cut_cm * qty / 10000`

Tape/loop/tie:

`weight_g = gsm_per_m * cut_cm * qty / 100`

LDPE liner:

`effective_gsm = micron * 1.84` for both tube walls, unless source provides GSM.

Rule level: `hard_constraint`.

## 11. Target vs Actual Weight Rules

- `bag_weight_target_g`: customer quoted/spec weight.
- `bag_weight_actual_g`: generated BOM total or historical sheet grand total.
- Do not overwrite one with the other.
- Target vs actual gap <= 10 percent is normal design tolerance.
- Target vs actual gap > 10 percent is a `soft_warning`, not a hard failure.
- Component sum vs generated actual must match within tolerance for generated BOM.

Rule level: target/actual warning is `soft_warning`.

