# Static Rule Tables

Status: Sprint 1 seed tables, revised after contract review.

Every row must declare one rule level:

- `hard_constraint`: validation rejects violations.
- `default_preference`: rule engine uses it when the customer did not specify.
- `fallback_heuristic`: use only when primary evidence is unavailable.

Machine-readable rules are physically separated:

- `rules/hard_constraints.json`
- `rules/defaults.json`
- `rules/heuristics.json`

Do not put default choices or ML advisories in hard constraints.

## Data Priors

Corrected dataset shape:

- 559 structured BOM records.
- Bag type distribution: 317 U-panel, 105 circular, 89 four-panel-baffle,
  23 single-loop, 11 two-loop, 10 four-panel, 4 two-panel.
- Common body GSM values: 125, 160, 140, 180, 120, 150, 210, 170, 130,
  185, 165, 200, 90, 195, 175.
- Common loop GPM values: 40, 30, 45, 35, 50, 28, 32, 55.
- Common accessory flags: DS spout 252 records, FS spout 229, baffle 89,
  liner 81, DDP 66.

## Canonical Component Dictionary

Rule level: `hard_constraint`.

| Canonical name | Common aliases from data |
|---|---|
| BODY PANEL | BODY PANEL |
| SIDE PANEL | SIDE PANNEL, SIDE |
| BOTTOM PANEL | BOTTOM PANNEL, BASE PANEL, BOTTOM |
| TOP PANEL | TOP PANNEL, TOP |
| TOP FLAP | TOP FLAP |
| SKIRT | TOP SKIRT, TOP/SKT, DUFFLE TOP |
| FILLING SPOUT | FILLING SPOUT, FS SPOUT, F/S, TOP SPOUT, TOP / FS |
| DISCHARGE SPOUT | D/S, D SPOUT, D/S SPOUT, BOTTOM SPOUT, DS SPOUT |
| BAFFLE | BAFFLE FABRIC, BAFFLE PANEL |
| DS FLAP | DS FLAP |
| DS PATCH | DS PATCH |
| LINER | LINER |
| CORNER LOOP | LOOP, LIFTING LOOP, LOOP LIFTING |
| FULL BODY LOOP | FULL LOOP |
| STEVEDORE LOOP | STEEVE DORE, STEEV DOOR LOOP, EXTRA LOOP |
| FS TIE | TIE/FS, FS TIE, FS/TAI |
| DS TIE | TIE/DS, IRISH TIE, TIE/IRIS ROPE, TIE/IRIS |
| PETAL TIE | PETAL TIE |
| TUCKING TIE | TUCKING TIE, TUCKING  TIE |
| DDP | DUST PROOF, DOUBLE DUST PROOF |
| DOC POCKET | DOC, DOCUMENT POCKET |
| LOOP PROTECTOR | LOOP PROTECTOR, LOOP RAINFORCE |
| TOP BAND | TOP BAND |
| BELLY BAND | BELLY BELT |
| TABBING | TABBING TAPE, TABBING |
| STITCHING | THREAD, STITCHING |
| PRINTING | PRINTING |
| LABEL | LABEL |

## Approved Width Tables

### Approved Loom Widths

Rule level: `hard_constraint` for generated fabric components.

The rule engine selects the nearest approved loom width at or above the formula
minimum. Validation checks generated fabric-area components against approved
loom widths only.

`[22, 24, 25, 26, 28, 30, 32, 40, 45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 56.5, 57, 58, 59, 60, 61, 63, 64, 65, 67, 68, 70, 70.5, 72.5, 73, 74, 75, 77, 78, 80, 81, 82, 83, 84, 85, 87, 88, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 125, 127, 128, 129, 130, 133, 136, 140, 144, 150, 160, 165, 169, 170, 175, 176, 180, 185, 187, 187.5, 190, 192, 193, 194, 195, 196, 198, 200, 204, 205, 210, 214, 215, 224, 255, 287]`

### Observed Component Widths

Observed historical widths are preserved separately in
`hard_constraints.json::observed_component_widths_cm`. They are useful for
retrieval, warnings, and data audit, but they are not the same concept as
generated loom-width legality.

### Tape Widths

Rule level: `hard_constraint` for loop/tie/DDP width fields.

- Loop webbing: 25, 40, 50, 55, 60, 65, 70, 72, 75, 76, 78, 80, 90, 95, 100 mm.
- Tie tape: 12, 15 mm.
- DDP/dust-proof cord: 3, 5, 6, 7, 7.5, 8, 9 mm.

## GSM and Load Threshold Rules

Rule level: `hard_constraint` for minimum structural GSM. This is not a final
engineered GSM-choice table. The U-panel engine uses this as the floor, then
uses historical defaults or the U-panel GSM advisory model to select a practical
value above the floor.

### Square Corner, SF 5:1

| SWL kg | Body GSM min | Bottom GSM min |
|---:|---:|---:|
| 0-250 | 70 | 70 |
| 251-500 | 110 | 110 |
| 501-750 | 120 | 120 |
| 751-1100 | 130 | 130 |
| 1101-1250 | 140 | 140 |
| 1251-1500 | 160 | 160 |
| 1501-1600 | 180 | 180 |
| 1601-1700 | 200 | 200 |
| 1701-1800 | 220 | 220 |
| 1801-1900 | 230 | 230 |
| 1901-2000 | 240 | 240 |

### Square Corner, SF 6:1 or UN

| SWL kg | Body GSM min | Bottom GSM min |
|---:|---:|---:|
| 0-250 | 110 | 110 |
| 251-500 | 130 | 130 |
| 501-750 | 130 | 130 |
| 751-1100 | 140 | 140 |
| 1101-1250 | 160 | 160 |
| 1251-1500 | 180 | 180 |
| 1501-1600 | 220 | 220 |
| 1601-1800 | 240 | 240 |

### Cross Corner, SF 5:1

| SWL kg | Body GSM min | Bottom GSM min |
|---:|---:|---:|
| 0-250 | 130 | 130 |
| 251-500 | 130 | 130 |
| 501-750 | 140 | 140 |
| 751-1100 | 155 | 155 |
| 1101-1250 | 165 | 165 |
| 1251-1500 | 170 | 170 |
| 1501-1600 | 180 | 180 |
| 1601-1700 | 200 | 200 |
| 1701-1800 | 220 | 220 |
| 1801-1900 | 230 | 230 |
| 1901-2000 | 240 | 240 |

### Cross Corner, SF 6:1 or UN

| SWL kg | Body GSM min | Bottom GSM min |
|---:|---:|---:|
| 0-250 | 110 | 110 |
| 251-500 | 130 | 130 |
| 501-750 | 130 | 130 |
| 751-1100 | 140 | 140 |
| 1101-1250 | 160 | 160 |
| 1251-1500 | 180 | 180 |
| 1501-1600 | 220 | 220 |
| 1601-1800 | 240 | 240 |

### Circular Fabric for 1/2 Loop Bags

Rule level: `hard_constraint` for single-loop and two-loop bag families.

| SF | SWL kg | Body GSM min | Bottom GSM min |
|---:|---:|---:|---:|
| 5 | 0-600 | 90 | 130 |
| 5 | 601-700 | 100 | 130 |
| 5 | 701-800 | 110 | 140 |
| 5 | 801-1000 | 140 | 160 |
| 5 | 1001-1250 | 150 | 170 |
| 5 | 1251-1500 | 190 | 230 |
| 6 | 0-600 | 100 | 130 |
| 6 | 601-700 | 110 | 130 |
| 6 | 701-800 | 120 | 140 |
| 6 | 801-1000 | 140 | 160 |
| 6 | 1001-1250 | 160 | 180 |
| 6 | 1251-1500 | 220 | 250 |

## Belt GPM / Width Rules

Rule level: `default_preference`. Validation may accept higher observed values.

| Loop family | SF | SWL kg | GPM | Width mm |
|---|---:|---:|---:|---:|
| corner_loop | 5 | 0-500 | 25 | 40 |
| corner_loop | 5 | 501-1000 | 30 | 40 |
| corner_loop | 5 | 1001-1250 | 35 | 50 |
| corner_loop | 5 | 1251-1500 | 35 | 50 |
| corner_loop | 5 | 1501-2000 | 50 | 50 |
| corner_loop | 6 | 0-500 | 30 | 40 |
| corner_loop | 6 | 501-750 | 35 | 40 |
| corner_loop | 6 | 751-1000 | 35 | 40 |
| corner_loop | 6 | 1001-1250 | 45 | 50 |
| corner_loop | 6 | 1251-1500 | 45 | 50 |
| corner_loop | 6 | 1501-2000 | 50 | 50 |
| cross_corner_loop | 5 | 0-500 | 30 | 50 |
| cross_corner_loop | 5 | 501-750 | 45 | 75 |
| cross_corner_loop | 5 | 751-1000 | 45 | 75 |
| cross_corner_loop | 5 | 1001-1250 | 50 | 75 |
| cross_corner_loop | 5 | 1251-1500 | 50 | 75 |
| cross_corner_loop | 5 | 1501-2000 | 60 | 80 |
| cross_corner_loop | 6 | 501-750 | 45 | 75 |
| cross_corner_loop | 6 | 751-1000 | 50 | 75 |
| cross_corner_loop | 6 | 1001-1500 | 50 | 75 |
| cross_corner_loop | 6 | 1501-2000 | 60 | 80 |

## U-Panel Geometry Rules

Source: `BAG_TYPE_-_UPANEL..pdf` and matching scan pages.

Rule level: formulas are `hard_constraint` for deterministic U-panel output.

| Component | Formula |
|---|---|
| BODY PANEL width | `nearest_approved_width(ext_W + 8)` |
| BODY PANEL cut | `2 * ext_H + ext_L + 10` |
| SIDE PANEL width | `nearest_approved_width(ext_W + 8)` |
| SIDE PANEL cut | `ext_H + 8` |
| TOP PANEL width/cut | `nearest_approved_width(ext_L + 8)` by `nearest_approved_width(ext_W + 8)` |
| FILLING SPOUT width | `nearest_approved_width(fs_spout_h_cm + 5)` |
| FILLING SPOUT cut | `fs_spout_dia_cm * 3.14 + 12` |
| DISCHARGE SPOUT height/width | `ds_spout_h_cm + 5 + ds_spout_dia_cm / 2 + 7` for iris |
| DISCHARGE SPOUT cut | `ds_spout_dia_cm * 3.14 + 12` |
| FS/DS tie | `125 cm`, 2 pcs when both ties combined, 6 or 7 g/m |
| IRIS tie | `ds_spout_dia_cm * 3.14 + 38` |
| Corner loop | `loop_LL_cm + loop_SL_cm + 50` |
| DDP | path length around bag/spouts, 4.5 g/m, doubled for double dust-proof |
| Doc pocket | `micron * width * cut * 2 * 0.92 / 10000` |
| Stitching | `0.45 * ext_H`, rounded up by rule engine |

## Component Presence Matrix

Rule level: `hard_constraint` for generated BOMs.

### Mandatory by Bag Type

| Bag type | Mandatory base components |
|---|---|
| `u_panel` | BODY PANEL, SIDE PANEL, CORNER LOOP, STITCHING, LABEL |
| `circular` | BODY PANEL, BOTTOM PANEL, CORNER LOOP, STITCHING, LABEL |
| `four_panel` | BODY PANEL, BOTTOM PANEL, CORNER LOOP, STITCHING, LABEL |
| `four_panel_baffle` | BODY PANEL, BOTTOM PANEL, BAFFLE, CORNER LOOP, STITCHING, LABEL |
| `two_panel` | BODY PANEL, BOTTOM PANEL, CORNER LOOP, STITCHING, LABEL |
| `single_loop` | BODY PANEL, BOTTOM PANEL, LOOP PROTECTOR, STITCHING, LABEL |
| `two_loop` | BODY PANEL, BOTTOM PANEL, LOOP PROTECTOR, STITCHING, LABEL |

### Mandatory by Top Type

| top_type | Additional mandatory components |
|---|---|
| `TOP_PANEL` | TOP PANEL |
| `SKIRT` | SKIRT |
| `TOP_FLAP` | TOP FLAP |
| `DUFFLE` | SKIRT |
| `OPEN_TOP` | none |

### Mandatory by Bottom Type and Closure

| Field | Additional mandatory components |
|---|---|
| `bottom_type=DISCHARGE_SPOUT` | DISCHARGE SPOUT, DS TIE |
| `bottom_type=IRIS` or `ds_closure=IRIS` | DISCHARGE SPOUT, DS TIE, iris DS TIE allowed as second DS TIE |
| `bottom_type=PETAL` or `ds_closure=PETAL` | DISCHARGE SPOUT, PETAL TIE |

### Mandatory by Accessory Flags

| Flag | Additional mandatory components |
|---|---|
| `has_fs_spout=true` | FILLING SPOUT, FS TIE |
| `has_ds_spout=true` | DISCHARGE SPOUT, DS TIE |
| `has_baffle=true` | BAFFLE |
| `has_liner=true` | LINER |
| `has_doc_pocket=true` | DOC POCKET |
| `has_ddp=true` | DDP |
| `has_stevedore=true` | STEVEDORE LOOP |

Optional components are not inserted into deterministic BOM merely because
retrieval may later suggest them. Retrieval suggestions remain advisory until
synthesis and validation.

## Component Policy Table

Rule level: `hard_constraint`.

Each canonical component has policy in `hard_constraints.json::component_policy`:

- component type: `fabric_area`, `linear`, `fixed_weight`, or
  `derived_special`;
- required fields;
- allowed nulls;
- allowed lamination values;
- duplicate policy.

This is why duplicate `DS TIE` can be legal for iris plus standard DS tie, while
duplicate `BODY PANEL` is rejected.

## Bag Type Classification

Rule level: `default_preference`; explicit customer wording wins.

| Raw phrase | Canonical bag type | Notes |
|---|---|---|
| U panel, U pannel, U+2 | `u_panel` | corner loop, 25-55 mm belt |
| Circular bag, tubular fabric | `circular` | cross-corner loop, 70-100 mm belt |
| 4 panel baffle, Q bag, anti bulge | `four_panel_baffle` | baffle mandatory |
| 4 panel | `four_panel` | baffle only when stated |
| Single loop | `single_loop` | loop free height often supplied |
| Double loop, two loop | `two_loop` | two-loop family |
| Two panel, C-type | `two_panel` | includes conductive Type C variants |
| Omega | `omega` | top stitching three times in double row |
| Platen | `platen` | must be explicitly mentioned |
| Box | `box` | must be explicitly mentioned |
| Tunnel | `tunnel` | tunnel height mentioned |
| Container | `container` | length commonly 5 m to 12 m |
| Conductive | `conductive` | Type C, conductive yarn |

## Weight Formula Rules

Rule level: `hard_constraint`.

- Fabric: `weight_g = gsm_area * width_cm * cut_cm * qty / 10000`.
- Tape/loop/tie/DDP: `weight_g = gsm_per_m * cut_cm * qty / 100`.
- LDPE tube/liner from micron: `effective_gsm = micron * 1.84`.
- Generated `computed_total_g` must equal sum of component weights.

## Validation Split

Hard failures:

- Schema invalid.
- Forbidden component name.
- Missing mandatory component.
- Fabric width not in approved width table.
- GSM below load threshold.
- Invalid lamination value.
- Generated component weight does not match formula.
- Generated total does not match component sum.
- Illegal bag type/top/bottom/accessory combination.

Soft warnings:

- Target vs actual gap above 10 percent.
- Historical record missing LABEL or has source total mismatch.
- Rare loop length/width combination.
- Retrieval disagreement.
- Low extractor confidence.
