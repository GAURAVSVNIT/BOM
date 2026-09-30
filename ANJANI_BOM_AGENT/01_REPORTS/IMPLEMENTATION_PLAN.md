# Anjani FIBC BOM Agent — Implementation Plan

**Version:** 1.1 — build-ready
**Date:** 26 August 2026
**Inputs closed:** All 44 questionnaire answers received. All 18 Part-1 rule sections verified and corrected by the engineer in `Rules from Data.pdf` (22 pages, handwritten). Every rule below re-tested against the 395-sheet corpus.
**Scope:** Costing excluded. Tape-plant / loom / needle-loom / INSTRACTION blocks included.

---

## Contents

| § | Section |
|---|---|
| 0 | What the rules PDF changed |
| 1 | The locked rule book |
| 2 | System architecture |
| 3 | Repository layout |
| 4 | Data contracts |
| 5 | The renderer |
| 6 | The solver |
| 7 | The validation gate |
| 8 | Data pipeline |
| 9 | Fine-tuning |
| 10 | Evaluation and acceptance gates |
| 11 | Build schedule |
| 12 | Open items and risks |
| 13 | Rules from the engineer notebook |

---
---

# 0 · What the rules PDF changed

Eleven rules confirmed as derived. **Nine corrected.** **Five entirely new rule tables** supplied that did not exist anywhere in the project before.

## 0.1 Corrections

| § | I derived | He ruled | Corpus check |
|---|---|---|---|
| 1.2 | U-panel body cut `2H + L + 10` (79%) | **`2H + L + 8`** — "+10" struck out, "8 cm" written | +8 on 6.9%, +10 on 79.3%. **He overrules the data.** Cost: 2.79 g on an 880 g bag = **0.32%** |
| 1.2 | U-panel top panel `(L+10) × (W+10)` | **`(L+8) × (W+8)`** | 44.8% at +8, 41% at +10 — near-even split, his call settles it |
| 1.3 | Circular body qty = 2 | **"2 walls = 1 PCS only"** | Sheets reconcile at ×2. Resolved as `pieces=1, wall_factor=2` — see §1.3 |
| 1.5 | 4-panel body cut `H + 7` | **`H + 8`** | +8 was already the runner-up |
| 1.5 | 4-panel top `(L+8.5) × (W+8.5)` | **`(L+10) × (W+10)`** | n=10, no strong mode |
| 1.6 | 29 loop misses need explaining | **"Please go with Actual calculation"** — the formula wins, the sheets are noise. `SL 730` is a typo for `78` | Formula stands at 87.2% |
| 1.10 | Yarn = flat constant per family | **Coefficient × bag height** — see §1.7 | Median err 14–15%; he labels it "approx" |
| 1.14 | Baffle corner-loop bottom GSM = "NA" | **Bottom GSM = body GSM**, filled in on every row | 89.7% of 203 sheets already identical |
| 1.14 | Cross-corner belt widths `78–100 / 85–100 …` | **All standardised to `75 mm`** | Removes eight ambiguous ranges |

## 0.2 New rules he supplied

1. **Lamination coating table** — coating GSM as a function of base GSM (§1.6).
2. **Yarn coefficient table** — six families plus container bags (§1.7).
3. **Belt width by loop type** — U+2 and corner 40–50 mm, cross-corner 70–100 mm (§1.5).
4. **Target weight = PO weight − 1%** (§1.8). This, not the PO figure, is the solver's set-point.
5. **Baffle fabric marking** — 38 + 32 + 38 = 108 cm plus 6 cm folding at both edges (§1.3).

## 0.3 The +8 / +10 conflict — closed, and why it barely matters

He ruled `2H + L + 8` against 79% of his own history. Two things make that safe:

- **The cost is 0.32% of bag weight** — 2.79 g on an 880 g bag, well inside the ±2% tolerance.
- **The model never emits a cut length.** Cut length is computed by the renderer from a rule table. Changing +8 to +10 is a one-line JSON edit plus a test re-run. No retraining, no data rebuild.

**Action:** implement **+8** as `hard_constraint`; record `+10` in the registry as `historical_variant` with its 79% frequency; tag every historical sheet that used +10 so it never contaminates a geometry regression test.

---
---

# 1 · The locked rule book

Final and code-ready. Provenance: `E` = engineer's ruling, `D` = derived and confirmed, `E+D` = both agree.

## 1.1 Weight formulas — `hard_constraint`

```
W1  fabric      weight_g = GSM x width_cm x cut_cm x qty / 10000              [E+D]
W2  tape/cord   weight_g = GPM x cut_cm x qty / 100                           [E+D]
                GPM = grams per metre, linear. Never g/m^2.
W3  LDPE liner  weight_g = micron x width_cm x length_cm x 2 x 0.92 / 10000   [E]
                his exact wording; algebraically identical to micron x 1.84
```

## 1.2 Classification — `hard_constraint`

```
FAMILY
  customer names a construction                  -> use it
  belt width >= 70 mm stated                     -> circular
  otherwise                                      -> u_panel (U+2)        [E, A1]
  genuinely ambiguous                            -> clarification, never guess

LOOP TYPE
  stated explicitly                              -> use it
  belt width 70-100 mm                           -> cross_corner
  otherwise                                      -> corner               [E, A2]

TOP
  nothing stated                                 -> OPEN_TOP             [E, E6]
  "spout filling" / "inlet spout" / a diameter   -> TOP_PANEL + filling spout
  skirt / duffle / top flap                      -> explicit confirmation only

Q BAG        == 4-panel baffle, always                                   [E, A6]
DOUBLE LAYER == 2 body fabrics AND 2 side fabrics per side               [E, A4]
STEVEDORE    == an attachment, not a family                              [E, A4]

ALIASES  U PANNEL = U-PANNEL = U PANEL BAG = U+2 = U+2 PANEL = U+2 PANNEL
```

Twelve families, no v1 subset [E, A5]:
`u_panel · circular · four_panel · four_panel_baffle · two_panel · single_loop · two_loop · omega · tunnel · tubular · h_bottom · container_liner`

## 1.3 Geometry — all from EXTERNAL L × W × H — `hard_constraint`

**U-PANEL (U+2)**

| Component | Width | Cut | Qty |
|---|---|---|---|
| Body | `W + 8` | `2H + L + 8` | 1 |
| Side | `L + 8` | `H + 8` | 2 |
| Top panel (if fitted) | `L + 8` | `W + 8` | 1 |
| Bottom panel | **NONE** — the U-piece forms it | | |
| Reinforcement | **NONE** — RF is cross-corner only | | |

**CIRCULAR / TUBULAR**

| Component | Width | Cut | Qty |
|---|---|---|---|
| Body | `W + L` (tube, **no seam allowance**) | `H + 8` | 1 pc / **wall_factor 2** |
| Top | `L + 10` | `W + 10` | 1 |
| Bottom | `L + 10` | `W + 10` | 1 |
| Side | **NONE** | | |

> **The circular-wall note.** He wrote *"2 walls = 1 PCS only"*. The tube physically has two walls, so fabric consumed is `2 × (W+L) × cut`, and the sheets reconcile at ×2. But it is **cut as one piece**. Implement two separate fields — `pieces_per_bag = 1` for the cutting and procurement sheets, `wall_factor = 2` inside the weight formula. Both his language and the arithmetic are then honoured, and the audit trail shows which is which.

**4-PANEL BAFFLE (Q-BAG)**

| Component | Width | Cut | Qty |
|---|---|---|---|
| Body | `W + 8` | `H + 8` | 4 |
| Top | `L + 8` | `W + 8` | 1 |
| Bottom | `L + 8` | `W + 8` | 1 |
| Baffle | see below | | 4 |

Baffle fabric: **width 108 cm = 38 + 32 + 38**, plus **6 cm for folding at both edges**. GSM `15 + 90 + 15` = 120, both-side laminated. Marking: 38 cm from corner to first baffle mark, 32 cm between marks, 38 cm from last mark to corner, double warp 2.5 cm on each mark, rest unmarked.

**4-PANEL (no baffle)**

| Component | Width | Cut | Qty |
|---|---|---|---|
| Body | `W + 8` | `H + 8` | 4 |
| Top | `L + 10` | `W + 10` | 1 |
| Bottom | `L + 8` | `W + 8` | 1 |

## 1.4 Spouts and closures — `hard_constraint`

```
Stated size is ALWAYS  diameter x height. First number = diameter. Always.  [E, B7]

cut_length = diameter x 3.14 + 12      FS 94.5% / DS 93.4% within 1.5 cm (n=311)
FS width   = height + 5
DS width   = height + 8

CLOSURE     extra fabric on width      tie
open        0                          none
tied        height + 8                 125 cm standard
iris        diameter / 2 + 6           diameter x 3.14 + 38,  2 ties
petal       same as base               diameter x 3.14 + 38
            + DS FLAP + DS PATCH
pyjama      diameter + 6               none additional
            (= spout + iris + iris, three layers)

The 38 cm on an iris tie = 10 + 10 cm outside each side
                         +  9 +  9 cm for the two knots.                    [E, B8]

A tie is MANDATORY wherever an FS, DS or Skirt exists, top or bottom.       [E, E1]
ROPE is a DIFFERENT component from TIE. Never merge them.                   [E, E1]
```

## 1.5 Loops and belt

```
loop_cut_cm = 2 x free_height + LL + SL       197/226 = 87.2% exact         [E+D]
loop_qty    = 4                               358/363 = 99%
weight      = GPM x cut_cm x qty / 100

DEFAULTS when the customer is silent                                        [E, D1]
  free_height = 25 cm
  LL          = 65% of bag height
  SL          = 35% of bag height

BELT WIDTH BY LOOP TYPE                                                     [E, p.10]
  U+2 panel     40 - 50 mm
  corner loop   40 - 50 mm
  cross corner  70 - 100 mm    (chart standardises to 75 mm for SWL >= 751)

BELT SELECTION                                                              [E, D2]
  default 50 mm unless the client specifies
  if computed belt weight < 25 g  ->  drop to 40 mm

BELT STRENGTH                                                               [E, D5]
  1 gram of belt carries 35 kg
  capacity_kg = GPM x 35 x loop_qty x legs        legs = 2   (open item O3)
  require  capacity_kg >= SWL x SF

OPTIONAL LOOP HARDWARE — explicit customer request only                     [E, D4]
  loop protector · extra loop · stevedore · full running loop
```

## 1.6 GSM and lamination

The load charts in `GSM- GPM VS SWL-SF.xlsx` are confirmed as-is, with two corrections:

- **4-panel-baffle corner-loop table:** the `NA` bottom column is filled in — **bottom GSM = body GSM** on every row (110 / 125 / 140 / 160 / 180 / 190 / 210 / 230 at 5:1; 120 / 135 / 150 / 170 / 200 / 220 / 230 at 6:1).
- **Cross-corner belt width column:** every `78–100`, `79–100`, `80–100`, `81–100`, `82–100`, `85–100`, `86–100`, `87–100`, `88–100`, `89–100`, `90–100` becomes **`75 mm`**.

```
SWL BANDS ARE EXCLUSIVE   751-1000 · 1001-1250 · ...                        [E, C4]
                          SWL exactly 1000 falls in 751-1000

WITHIN A CHART RANGE      the deciding factor is BAG WEIGHT                 [E, C5]
                          e.g. 240 gsm gives 3.1 kg -> use 230 to hit 3.0

CUSTOMER OVERRIDE         a customer-stated GSM below the chart minimum     [E, C6]
                          is HONOURED. Warn, raise a clarification,
                          never reject.

COMPONENT GSM                                                               [E, C9]
  bottom_gsm = body_gsm                     89.7% confirmed on 203 sheets
  if bag_weight >= 2.5 kg: top = bottom = body
  baffle = 15 + 90 + 15 = 120  both-side laminated
  spout  = 70 + 20 = 90
  heavy-duty -> higher GSM per client requirement

NOTATION                                                                    [E, C7/C8]
  the GSM column ALWAYS holds the TOTAL, never the base
  "70+20 LAMINATED"     -> GSM column reads 90
  "15+90+15"            -> both-side lamination, 120 total (baffle standard)
  "175+30 UNLAMINATED"  -> CLERICAL ERROR. It IS laminated. Repair on ingest.
```

**LAMINATION COATING TABLE — new, `default_preference`, PO overrides it** [E, p.6]

| Base GSM | Coating GSM |
|---|---|
| 50 – 65 | 15 |
| 66 – 130 | 20 |
| 131 – 150 | 25 |
| 151 – 210 | 30 |
| 211 – 240 | 35 |

> Corpus check: **64.4% exact** on 626 laminated rows. Mismatches cluster at two band edges — base 60–65 used 20 (table says 15), and base 155–170 used 25 (table says 30). Implement as given, log every deviation. If deviation stays above 30% after phase 3, take the measured bands back to him. His instruction: *"lamination as per above; if anything else is mentioned in the PO, please go with this."*

## 1.7 Sewing yarn — `default_preference`

**Approximate yarn cut calculation = coefficient × bag height** [E, p.9]

| Family | Coefficient | Corpus median error |
|---|---|---|
| U+2 panel | **0.45 × H** | 14.9% (n=174) |
| 4-panel | **0.65 × H** | 15.0% (n=11) |
| 4-panel baffle | **0.70 × H** | 14.3% (n=70) |
| Circular | **0.50 × H** | 14.5% (n=109) |
| Single loop | **0.25 × H** | 64.0% (n=14) — open item O4 |
| Two loop | **0.30 × H** | 11.2% (n=6) |
| Container bag 40 ft | **300 g** flat | — |
| Container bag 20 ft | **150 g** flat | — |

He labelled this "approx". A 15% error on yarn is **0.7% of bag weight** — inside ±2% and correctable by the solver.

```
YARN SPECIFICATION                                                          [E, F3]
  white  3000 - 3200 DNR   safety stitching   (default)
  blue   3600 DNR          Hirakal overlock
```

## 1.8 Target weight and tolerance — `hard_constraint`

```
TARGET    =  PO bag weight x 0.99      <- "PO Bag weight minus 1%"          [E, p.7]
TOLERANCE =  +/- 2%                                                         [E, G1]

SOLVER KNOB ORDER                                                           [E, G3]
  1. loop gramage (GPM)
  2. loop cut length (free height / LL / SL)
  3. body GSM  — only within market-standard values for the load
  each step surfaced to the client, confirmation taken

MODE SELECTION                                                              [E, C2]
  PO states a bag weight   ->  BACKWARD  (solve for it)
  PO states none           ->  FORWARD   (chart GSM, chart belt, report weight)

"BAG WT."  = what Anjani computed and quoted back                           [E, G4]
"REQ. WT." = what the customer asked for
             Two separate fields. Never merge.
```

## 1.9 Dust-proofing and DDP — `hard_constraint`

```
DDP = DOUBLE DUST PROOF  (not a discharge port)                             [E, E3]
weight = total_stitching_length_m x 2 x 4.5 g/m       "DDP as per stitching mtr"
         Resolves the old qty-100 anomaly: cm was being read as metres.

THREE GRADES                                                                [E, E4]
  1. filler cord / dust proof     ("filler cord" and "dust proof" are aliases)
  2. double dust proof (DDP)
  3. triple dust proof            = double dust proof + FELT
```

## 1.10 Component catalogue — `hard_constraint`

The 15-row template gains **five rows** he wrote in [E, p.16]: `ROPE`, `B-LOCK`, `GLUE`, `TABBING TAPE`, and an `EXTRA COMPONENT` category.

| Canonical | Raw labels that map to it |
|---|---|
| DISCHARGE SPOUT | `D/S` · `D SPOUT` · `DS SPOUT` · `DISCHARGE SPOUT` · `BOTTOM SPOUT` · `D/ SPOUT` · **`OUTLET SPOUT`** |
| FILLING SPOUT | `FILLING SPOUT` · `FS SPOUT` · `F/S` · `TOP SPOUT` · `TOP / FS` · `TOP` · **`INLET SPOUT`** — **`TOP/SKT` EXCLUDED** |
| SKIRT | `SKIRT` · `DUFFLE` · `TOP/SKT` — **a separate attachment, never a filling spout** |
| SIDE PANEL | `SIDE PANNEL` · `SIDE PANEL` |
| TOP PANEL | `TOP PANNEL` · `TOP PANEL` |
| BOTTOM PANEL | `BOTTOM PANNEL` · `BOTTOM PANEL` · **`BASE PANEL`** |
| BAFFLE | `BAFFLE` · `BAFFLE FABRIC` |
| IRIS TIE | `TIE/IRIS ROPE` · `IRISH TIE` · `TIE/IRIS` · `BRAIDED ROPE` |
| FS TIE / DS TIE | `FS TIE` · `DS TIE` · `TIE` · `FS/DS TIE` · `F/S & D/S TIE` · `FS & DS TIE` · `F/S , D/S TIE` · `DS/FS TIE` · `TIE/DS` · `FS/ DS TIE` · `SUPPORTING TIE` · `TUCKING TIE` · `SKIRT TIE` |
| STEVEDORE LOOP | `STEEVE DORE` · `STEEVEDORE` |
| BELLY BAND | `BELLY BEND` · `BELLY BELT` |
| FILLER CORD | `FILLERCORD` · **`DUST PROOF`** |
| ROPE | `ROPE` — **distinct from TIE** |
| EXTRA COMPONENT | `FELT` · `GLUE` · `TABBING TAPE` · `TOP BEND` · `DS FLAP` · `DS PATCH` · `LOOP PROTECTOR` · `EXTRA LOOP` · `B-LOCK` |

**When each rare component is fitted** — all client-specified [E, E2]:
`FELT` triple dust-proof only · `GLUE` liner glued · `TABBING TAPE` liner tabbed at 4 or 8 points (the alternative to gluing) · `BELLY BAND` "stomach belt" · `TOP BAND` an attachment · `DS FLAP` and `DS PATCH` petal closures only.

**Never added silently** [E, E5/E7]: liner, doc pocket, printing. Liner insertion defaults to **loose**; micron and method always client-specified.

## 1.11 Stitching and folding — `default_preference`

```
overlock + chain == HR + DR        same thing, and the DEFAULT              [E, F2]
double needle / double chain       client-specified only
single fold                        the standard
out-fold == butterfly              the DEFAULT fold — NOT J-fold
J-fold                             an alternative to out-fold
"box J fold", "top hemming"        DO NOT EXIST at Anjani.
                                   Strip from the corpus on ingest.
```

## 1.12 Raw material and static type

```
MIXING       PP / CC / UV / RP                                              [E, F6]
             observed  PP 80   / CC 8  / UV 1.5 / RP 12.5
                       PP 80.5 / CC 8  / UV 1.5 / RP 10
                       PP 88.5 / CC 10 / UV 1.5           (85x85x85 reference)
             "standard, changed as per our understanding"  -> default_preference

STATIC TYPE  A plain woven, non-flammable only
             B low breakdown voltage, dry flammable powders, no solvents
             C conductive threads, MUST be grounded
             D static-dissipative, no grounding                    [E, confirmed]

GOVERNING STANDARD  ISO 21898 / AS 3668 — he marked "need to check".
                    Do NOT print a standards claim on any output until confirmed.
```

---
---

# 2 · System architecture

```
                    ┌──────────────────────────────────────────┐
                    │ 0 · INGEST                               │
                    │ WhatsApp · email · PDF TDS · scan → OCR  │
                    └───────────────────┬──────────────────────┘
                                        ▼
                    ┌──────────────────────────────────────────┐
                    │ 1 · EXTRACTION — QWEN ADAPTER A          │   model
                    │ → OrderSpec. Only what the PO says.      │
                    │ Missing stays missing. Never invents.    │
                    └───────────────────┬──────────────────────┘
                                        ▼
                    ┌──────────────────────────────────────────┐
                    │ 2 · DERIVE + CLASSIFY                    │   code
                    │ SWL from density × volume if absent      │
                    │ family / loop / top by fixed rule §1.2   │
                    └───────────────────┬──────────────────────┘
                  ┌─────────────────────┼─────────────────────┐
                  ▼                                           ▼
      ┌────────────────────────┐              ┌────────────────────────┐
      │ 3 · RETRIEVAL          │              │ 4 · RULE ENVELOPE      │
      │ top-3 nearest built    │              │ GSM band · belt band   │
      │ weighted by PRODUCT    │              │ mandatory components   │
      │ + geometry             │              │ lamination coating     │
      └────────────┬───────────┘              └───────────┬────────────┘
                   └─────────────────┬─────────────────────┘
                                     ▼
                    ┌──────────────────────────────────────────┐
     ┌── SOLVER ───▶│ 5 · CONFIGURATION — QWEN ADAPTER B      │   model
     │              │ → BuildSpec · ~70 closed-vocab decisions │
     │              │ no widths · no cuts · no weights         │
     │              └───────────────────┬──────────────────────┘
     │                                  ▼
     │              ┌──────────────────────────────────────────┐
     │              │ 6 · RENDERER — deterministic             │   code
     │              │ geometry → qty → weights → grand total   │
     │              │ NO loom snapping (B6)                    │
     │              └───────────────────┬──────────────────────┘
     │                                  ▼
     │   knobs in    ┌─────────────────────────────────────────┐
     │   order:      │ 7 · WEIGHT SOLVER                       │   code
     │   1 loop GPM  │ target = PO weight × 0.99, ±2%          │
     │   2 loop cut  │ backward if weight given, else forward  │
     │   3 body GSM  │ max 3 passes                            │
     └───────────────┴───────────────────┬─────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │ 8 · VALIDATION GATE — 21 checks          │   code
                    │ recompute every line from its own geom.  │
                    └───────────────────┬──────────────────────┘
                                        ▼
                    ┌──────────────────────────────────────────┐
                    │ 9 · DUAL OUTPUT                          │
                    │ BOM sheet  +  CLARIFICATION LIST         │
                    │ construction type shown FIRST (H5)       │
                    └──────────────────────────────────────────┘
```

**The invariant.** Draw a line through the middle. Above it the model chooses from finite sets. Below it code does arithmetic. **No value ever crosses that line in the wrong direction.** Everything else in this document is detail.

**Two stages deleted** versus the earlier draft: loom-width snapping (B6 — the loom is set to whatever the calculation says) and the separate infeasibility path (folded into the clarification engine, because C6 means nothing is truly infeasible — the customer can always override).

---
---

# 3 · Repository layout

```
bom_agent/
├── pyproject.toml
├── README.md
│
├── rules/                          THE RULE TABLES — data, not code
│   ├── registry/
│   │   ├── geometry.json           §1.3, per family, with provenance + agreement
│   │   ├── spouts.json             §1.4, cut/width/closure
│   │   ├── loops.json              §1.5, formula + defaults + belt width bands
│   │   ├── gsm_charts.json         §1.6, all six charts, corrected
│   │   ├── lamination.json         §1.6, the 5-band coating table
│   │   ├── yarn.json               §1.7, coefficients per family
│   │   ├── components.json         §1.10, canonical list + alias map + fit rules
│   │   ├── stitching.json          §1.11
│   │   ├── materials.json          §1.12, mixing + static types
│   │   ├── bulk_density.json       digitised from the National Bulk Bag PDF
│   │   └── taxonomy.json           §1.2, family + loop classification patterns
│   └── loader.py                   the ONLY module that reads the registry
│
├── contracts/                      Pydantic, extra="forbid" everywhere
│   ├── enums.py                    every closed vocabulary
│   ├── order_spec.py               §4.1
│   ├── build_spec.py               §4.2
│   ├── physical_bom.py             §4.3
│   ├── clarification.py            §4.4
│   └── audit.py
│
├── ingest/
│   ├── text.py                     plain text passthrough
│   ├── pdf.py                      PyMuPDF text layer
│   ├── ocr.py                      scans and photos
│   └── normalise.py                units: inch→cm, gr/m2→GSM, kg→g, 5:01→5:1
│
├── extraction/
│   ├── adapter_a.py                Qwen A client, grammar-constrained
│   ├── regex_fallback.py           the old normaliser, kept as automatic fallback
│   └── evidence.py                 span verification — the hallucination check
│
├── classify/
│   ├── family.py                   §1.2
│   ├── swl.py                      density × volume derivation
│   └── envelope.py                 §1.6 bands + mandatory set
│
├── retrieval/
│   ├── index.py                    geometric + categorical + PRODUCT
│   └── advisory.py                 line-level diff vs neighbours
│
├── configure/
│   ├── adapter_b.py                Qwen B client, grammar-constrained
│   └── deterministic.py            the no-model fallback configurer
│
├── render/
│   ├── geometry.py                 §5.1 — widths and cuts
│   ├── quantities.py               §5.2 — per-family qty + wall_factor
│   ├── weights.py                  §5.3 — W1/W2/W3
│   ├── stitching.py                §5.4 — yarn + DDP seam length
│   └── assemble.py                 §5.5 — the PhysicalBOM
│
├── solve/
│   └── weight_solver.py            §6
│
├── validate/
│   ├── gate.py                     §7, 21 checks
│   └── checks/                     one module per check, individually testable
│
├── clarify/
│   └── engine.py                   §4.4 — what to ask the customer
│
├── output/
│   ├── xlsx.py                     the four-block Anjani sheet
│   ├── csv.py
│   └── audit.py                    per-field provenance
│
├── pipeline.py                     wires 0→9
├── cli.py
│
├── data/
│   ├── raw/                        All_Things (read-only, content-hashed)
│   ├── gold/
│   │   ├── order_spec.jsonl        one per sheet, HEADER BLOCK ONLY
│   │   ├── build_spec.jsonl        one per sheet, full sheet
│   │   ├── physical_bom.jsonl      component table verbatim — renderer tests only
│   │   └── clarification.jsonl     derived from OrderSpec gaps
│   ├── train/  val/  test/         fingerprint-split
│   └── eval_real/                  ~30 hand-labelled real PDFs and scans
│
├── tools/
│   ├── build_gold.py               §8.2
│   ├── dedupe.py                   §8.3
│   ├── split.py                    §8.3
│   ├── build_extractor_set.py      §8.4
│   ├── train_a.py   train_b.py     §9
│   ├── evaluate.py                 §10
│   └── digitise_density.py         bulk density PDF → JSON
│
└── tests/
    ├── test_geometry.py            every rule against its corpus agreement
    ├── test_renderer_replay.py     all 395 sheets, BuildSpec_gold → PhysicalBOM_gold
    ├── test_solver.py
    ├── test_gate.py
    ├── test_firewall.py            OrderSpec fields ⊆ header cells — MUST FAIL LOUD
    ├── test_no_leakage.py          train ∩ val fingerprints = ∅
    └── regression/                 the 20 fixed cases incl. 85×85×85
```

**Design rule:** `rules/registry/*.json` is the single source of truth for every constant. No number is ever written in Python. Every entry carries `rule_id`, `rule_level` (`hard_constraint` / `default_preference` / `historical_variant`), `source` (`engineer_2026_08` / `corpus` / `published`), and `agreement` where measured.

---
---

# 4 · Data contracts

## 4.1 OrderSpec — what the customer said

Built from the **header block alone**. Every field carries a state, so "the customer did not say" is a first-class value and hallucination becomes measurable.

```jsonc
{
  "source": {"type": "pdf_tds", "file": "SPEC JIEXP-051.pdf", "lang": "en",
             "ocr_confidence": null},

  "customer":          {"value": "JUMBOCEL", "state": "provided", "evidence": "Company CODE: JIEXP-051"},
  "order_no":          {"value": null, "state": "not_specified"},
  "product_contents":  {"value": "china clay", "state": "provided", "evidence": "..."},
  "bulk_density_kg_m3":{"value": 1010, "state": "derived", "source": "bulk_density.json"},

  "ext_L_cm":          {"value": 103, "state": "provided", "evidence": "SIZE: 103 X 103 X 200 cms"},
  "ext_W_cm":          {"value": 103, "state": "provided"},
  "ext_H_cm":          {"value": 200, "state": "provided"},
  "int_L_cm":          {"value": null, "state": "not_specified"},
  "fill_volume_m3":    {"value": null, "state": "not_specified"},

  "swl_kg":            {"value": 1500, "state": "provided", "evidence": "SAFE WORKING LOAD: 1500 KGS."},
  "sf":                {"value": "5:1", "state": "provided"},
  "req_weight_g":      {"value": null, "state": "not_specified"},   // customer's ask
  "stated_body_gsm":   {"value": 220,  "state": "provided", "evidence": "FABRIC: 220 gr/m2"},

  "stated_family":     {"value": "u_panel", "state": "provided", "evidence": "PRODUCTION LINE: U-PANEL"},
  "stated_loop_type":  {"value": null, "state": "not_specified"},
  "belt_width_mm":     {"value": 76.2, "state": "provided", "evidence": "3\" PP white"},
  "loop_free_height_cm":{"value": 30, "state": "provided"},
  "loop_LL_cm":        {"value": null, "state": "not_specified"},
  "loop_SL_cm":        {"value": null, "state": "not_specified"},

  "top_type":          {"value": "SKIRT", "state": "provided", "evidence": "DUFFLE TOP 90 cm height"},
  "skirt_height_cm":   {"value": 90, "state": "provided"},
  "bottom_type":       {"value": "DS_SPOUT", "state": "provided"},
  "ds_dia_cm":         {"value": 80, "state": "provided", "evidence": "80 cm Dia x 60 cm long"},
  "ds_height_cm":      {"value": 60, "state": "provided"},
  "ds_closure":        {"value": "X_CUT_B_LOCK", "state": "provided"},

  "has_liner":         {"value": null, "state": "not_specified"},
  "has_doc_pocket":    {"value": true, "state": "provided", "evidence": "12 x 15\" zip lock"},
  "printing_sides":    {"value": 2, "state": "provided"},
  "printing_colors":   {"value": "4+2", "state": "provided"},
  "packing":           {"value": "125 per pallet", "state": "provided"},
  "static_type":       {"value": null, "state": "not_specified"},

  "special_notes":     ["UV 70% strength retention after 1200 hr Xenon"],
  "raw_text":          "...the full normalised enquiry text..."
}
```

**`state`** is one of `provided` · `not_specified` · `derived` · `repaired`.
**`evidence`** must be a verbatim substring of `raw_text`. If it is not, the field is a hallucination — checked automatically, no human needed.

## 4.2 BuildSpec — what the engineer decides

~70 fields. Every one is an enum member, a boolean, or a value from a closed catalogue. **Not one is a computed quantity.**

```jsonc
{
  // ── construction ────────────────────────────────────────────
  "family": "u_panel",              // enum, 12 values
  "loop_type": "corner",            // corner | cross_corner | single | full_running
  "static_type": "A",               // A | B | C | D
  "double_layer": false,
  "top_type": "OPEN_TOP",           // OPEN_TOP | TOP_PANEL | SKIRT | TOP_FLAP | FS_SPOUT
  "bottom_type": "FLAT_BOTTOM",     // FLAT_BOTTOM | DS_SPOUT

  // ── materials ───────────────────────────────────────────────
  "body_gsm": 150,                  // from GSM_CATALOGUE
  "body_laminated": false,
  "body_lami_gsm": null,            // renderer fills from lamination.json if laminated
  "bottom_gsm": null,               // null ⇒ renderer sets = body_gsm  (C9)
  "top_gsm": null,
  "spout_gsm": 90,                  // 70+20 default
  "baffle_gsm": null,               // 120 (15+90+15) when family is baffle
  "fabric_colour": "WHITE",
  "rm_blend": {"PP": 88.5, "CC": 10.0, "UV": 1.5, "RP": 0.0},

  // ── loops ───────────────────────────────────────────────────
  "loop_qty": 4,
  "belt_width_mm": 50,              // enum
  "belt_gpm": 35,                   // enum, must sit inside envelope.belt_band
  "loop_free_height_cm": 25,
  "loop_attach_long_cm": 65,        // default 0.65 × H
  "loop_attach_short_cm": 35,       // default 0.35 × H
  "loop_colour": "WHITE",
  "loop_stitch": "6_PASS_JUKKI_OUTSIDE",

  // ── component switches ──────────────────────────────────────
  "has_baffle": false,
  "has_liner": false, "liner_micron": null, "liner_fit": null,
  "liner_insertion": null,          // LOOSE (default) | TABBED_4 | TABBED_8 | GLUED | HEMMED
  "has_doc_pocket": false, "doc_size": null,
  "dust_proof": "SINGLE",           // NONE | SINGLE | DOUBLE | TRIPLE
  "has_felt": false,                // TRIPLE implies this
  "has_b_lock": false, "has_tabbing_tape": false, "has_glue": false, "has_rope": false,
  "has_stevedore": false, "has_belly_band": false, "has_top_band": false,
  "has_loop_protector": false, "has_extra_loop": false,
  "printing_sides": 0, "printing_colors": null,
  "has_label": true,

  // ── spouts ──────────────────────────────────────────────────
  "fs_dia_cm": null, "fs_height_cm": null, "fs_closure": null,
  "ds_dia_cm": null, "ds_height_cm": null, "ds_closure": null,
  "skirt_height_cm": null,

  // ── production ──────────────────────────────────────────────
  "yarn_white_denier": 3200,        // 3000 | 3200
  "yarn_blue_denier": 3600,
  "stitch_spec": "OVERLOCK_CHAIN",  // == HR_DR
  "fold_spec": "OUT_FOLD",          // == BUTTERFLY (default) | J_FOLD
  "packing_per_pallet": 500,
  "instruction_lines": ["U PANNEL BAG WITH CORNER LOOP", "BAG WT +/-2 %"],

  // ── provenance, one entry per decided field ─────────────────
  "_provenance": {
    "body_gsm": {"src": "solver", "reason": "target 871 g (880 × 0.99) at ±2%; chart floor 140 permits 150"},
    "belt_gpm": {"src": "retrieval", "reason": "neighbour SHEET-0412, same SWL band, same product"},
    "family":   {"src": "default", "reason": "construction not stated, belt < 70 mm; house default U+2"},
    "loop_attach_long_cm": {"src": "rule", "reason": "0.65 × H, customer silent"}
  }
}
```

## 4.3 PhysicalBOM — what gets cut

Produced entirely by code. Shown for the 85×85×85 reference under the **corrected +8 rule**:

```jsonc
{
  "components": [
    {"sr": 1, "name": "BODY PANEL", "gsm": 150, "lami": "UNLAMINATED", "colour": "WHITE",
     "width_cm": 93, "cut_cm": 263, "pieces": 1, "wall_factor": 1, "weight_g": 366.885,
     "rule_id": "geom.u_panel.body", "formula": "150 × 93 × 263 × 1 / 10000",
     "note": "cut = 2(85) + 85 + 8"},

    {"sr": 2, "name": "SIDE PANEL", "gsm": 150, "lami": "UNLAMINATED", "colour": "WHITE",
     "width_cm": 93, "cut_cm": 93, "pieces": 2, "wall_factor": 1, "weight_g": 259.470,
     "rule_id": "geom.u_panel.side", "formula": "150 × 93 × 93 × 2 / 10000"},

    {"sr": 3, "name": "CORNER LOOP", "gpm": 35, "width_mm": 50, "colour": "WHITE",
     "cut_cm": 150, "pieces": 4, "weight_g": 210.000,
     "rule_id": "geom.loop.cut", "formula": "35 × 150 × 4 / 100",
     "note": "cut = 2(25) + 65 + 35"},

    {"sr": 4, "name": "STITCHING", "spec": "3200 DNR WHITE + 3600 DNR BLUE",
     "weight_g": 38.25, "rule_id": "yarn.u_panel", "formula": "0.45 × 85"},

    {"sr": 5, "name": "LABEL", "weight_g": 2.0, "rule_id": "component.label.flat"}
  ],
  "grand_total_g": 876.605,
  "po_weight_g": 880.0,
  "target_weight_g": 871.2,           // 880 × 0.99
  "deviation_from_target_pct": 0.62,  // inside ±2%  ✓
  "loom_requirement": [...],
  "procurement": []
}
```

> Note the two rule changes visible here: cut 263 comes from `+8` (unchanged for this bag, which already used +8), and yarn is now `0.45 × 85 = 38.25 g` rather than the sheet's 40 g — a 1.75 g difference, 0.2% of the bag.

## 4.4 ClarificationList — what to ask the customer

A co-equal output, not an error path. G2 and G5 make this a product feature.

```jsonc
{
  "blocking": [
    {"code": "SWL_MISSING",
     "question": "SWL is not stated. Please confirm the safe working load, or tell us the product and fill volume so we can compute it.",
     "why": "SWL and SF drive the fabric GSM floor and the belt selection."}
  ],
  "advisory": [
    {"code": "GSM_BELOW_CHART",
     "question": "You have specified 150 GSM. Our standard for a corner-loop bag at SWL 1000 kg / 5:1 is 140 GSM minimum, and 150 GSM gives a finished weight of 878 g against your stated 720 g. Shall we proceed against the bag weight, or against the specified GSM?",
     "options": [
        {"label": "against bag weight", "implies": {"body_gsm": 112, "total_g": 720, "warning": "below the 140 GSM standard"}},
        {"label": "against stated GSM",  "implies": {"body_gsm": 150, "total_g": 878}}
     ],
     "why": "C6 — customer-stated GSM is honoured, but the trade must be explicit."},

    {"code": "LOOP_LENGTH_ASSUMED",
     "question": "Loop attachment lengths were not stated. We have assumed LL 55 cm and SL 30 cm (65% / 35% of bag height) with 25 cm free height. Please confirm.",
     "why": "D1 — LL/SL come from the customer when available."}
  ],
  "assumptions_made": [
    {"field": "family", "value": "u_panel", "reason": "not stated, belt < 70 mm, house default"},
    {"field": "top_type", "value": "OPEN_TOP", "reason": "not stated"},
    {"field": "liner", "value": false, "reason": "not stated — never added silently"}
  ]
}
```

---
---

# 5 · The renderer

Pure arithmetic. Deterministic. Every number in the finished sheet is born here and nowhere else.

## 5.1 Geometry — `render/geometry.py`

```python
def widths_and_cuts(build: BuildSpec, spec: OrderSpec, rules) -> list[ComponentGeom]:
    L, W, H = spec.ext_L_cm, spec.ext_W_cm, spec.ext_H_cm
    g = rules.geometry[build.family]          # from geometry.json — never hard-coded

    out = []
    # body
    out.append(ComponentGeom("BODY PANEL",
        width = evaluate(g.body.width, L=L, W=W, H=H),   # "W + 8"
        cut   = evaluate(g.body.cut,   L=L, W=W, H=H),   # "2*H + L + 8"
        pieces= g.body.pieces,                            # 1 | 4
        walls = g.body.wall_factor))                      # 1, or 2 for circular

    # side panels — u_panel only
    if g.side:
        out.append(ComponentGeom("SIDE PANEL",
            width=evaluate(g.side.width, L=L, W=W, H=H), # "L + 8"
            cut  =evaluate(g.side.cut,   L=L, W=W, H=H), # "H + 8"
            pieces=2 * (2 if build.double_layer else 1))  # A4: double layer doubles sides

    # ... top, bottom, baffle per family
    return out
```

**Double layer** (A4) multiplies **body pieces AND side pieces** by 2 — not the GSM, not the width.

## 5.2 Spouts — `render/geometry.py`

```python
def spout(dia_cm, height_cm, kind, closure, rules) -> ComponentGeom:
    cut   = dia_cm * 3.14 + 12                              # B7
    width = height_cm + (5 if kind == "FS" else 8)          # B7

    extra = {                                               # B8
        "open":   0,
        "tied":   height_cm + 8,
        "iris":   dia_cm / 2 + 6,
        "petal":  0,
        "pyjama": dia_cm + 6,
    }[closure]
    return ComponentGeom(f"{kind} SPOUT", width=width + extra, cut=cut, pieces=1)


def spout_tie(dia_cm, closure) -> list[ComponentGeom]:
    if closure == "open":
        return []
    if closure == "tied":
        return [ComponentGeom("TIE", cut=125, pieces=1)]
    if closure in ("iris", "petal"):
        return [ComponentGeom("IRIS TIE", cut=dia_cm * 3.14 + 38, pieces=2)]
    return []                                               # pyjama adds no tie
```

A tie is **mandatory** wherever an FS, DS or Skirt exists (E1) — enforced by validator V07, not left to the model.

## 5.3 Weights — `render/weights.py`

```python
def fabric_weight(gsm, width_cm, cut_cm, pieces, walls=1):
    return gsm * width_cm * cut_cm * pieces * walls / 10000        # W1

def tape_weight(gpm, cut_cm, pieces):
    return gpm * cut_cm * pieces / 100                             # W2

def liner_weight(micron, width_cm, length_cm):
    return micron * width_cm * length_cm * 2 * 0.92 / 10000        # W3
```

## 5.4 Stitching and DDP — `render/stitching.py`

```python
YARN_COEFF = rules.yarn.coefficients      # u_panel 0.45, circular 0.50, baffle 0.70 ...

def yarn_weight(family, H_cm, container_ft=None):
    if family == "container_liner":
        return {40: 300.0, 20: 150.0}[container_ft]
    return YARN_COEFF[family] * H_cm                                # §1.7

def ddp_weight(seam_length_m):
    return seam_length_m * 2 * 4.5                                  # E3 — double dust proof
```

`seam_length_m` is computed from the assembled geometry — the perimeter of every stitched joint for the chosen family and fold spec. It is **not** a model output.

## 5.5 Assembly order — `render/assemble.py`

1. resolve GSM defaults (`bottom_gsm = body_gsm` if null; `top = bottom = body` if bag ≥ 2.5 kg)
2. resolve lamination coating from `lamination.json` for every laminated component
3. compute widths and cuts for all structural panels
4. compute spouts and their ties
5. compute loops
6. compute optional components in canonical order
7. compute seam length → DDP
8. compute yarn
9. add label (flat 2 g) and printing (flat, per side)
10. sum → `grand_total_g`
11. build `loom_requirement` (regroup by fabric width + GSM + colour)
12. build `procurement` (bought-out items: liner, B-lock, doc pocket, filler cord)

---
---

# 6 · The solver

```python
def solve(spec: OrderSpec, build: BuildSpec, rules, max_passes=3):
    if spec.req_weight_g.state != "provided":
        # FORWARD mode — C2
        return render(build), None

    target = spec.req_weight_g.value * 0.99            # "PO Bag weight minus 1%"  [E, p.7]
    tol    = 0.02                                      # ±2%                        [E, G1]

    history = []
    for p in range(max_passes):
        bom = render(build)
        gap = bom.grand_total_g - target
        if abs(gap) / target <= tol:
            return bom, None                           # converged

        history.append({"pass": p, "build": build.digest(), "total": bom.grand_total_g})

        # KNOB ORDER IS THE ENGINEER'S, NOT OURS  [E, G3]
        moved = (try_loop_gpm(build, gap, rules)            # 1
              or try_loop_cut(build, gap, rules)            # 2
              or try_body_gsm(build, gap, rules))           # 3
        if not moved:
            break

    # did not converge — do NOT force it. Present the trade.  [E, G2]
    return bom, build_clarification(spec, build, bom, target, history)
```

**Knob 1 — loop gramage.** Move `belt_gpm` one step within the chart band for this SWL/SF, honouring `capacity ≥ SWL × SF`. If the resulting belt weight drops below 25 g, also drop the width to 40 mm (D2).

**Knob 2 — loop cut length.** Adjust free height, then LL/SL around the 65/35 split, staying inside the observed ranges (FH 22–122, LL 30–140, SL 30–96).

**Knob 3 — body GSM.** Step through the family's GSM catalogue, but only within values that are market-standard for the load — never below the chart floor unless the customer explicitly stated a lower GSM (C6).

**Why loop first.** He was explicit, and the physics agrees: on the 85×85×85 reference the loops are 210 g of an 878 g bag (24%) and the belt band 30–35 GPM gives ±30 g of adjustment range without touching the fabric that carries the load.

---
---

# 7 · The validation gate

Twenty-one checks. Note the severities — several are **warnings**, because C6 makes the customer's word final.

| # | Check | Rule | Severity |
|---|---|---|---|
| V01 | Arithmetic | every component weight recomputed from its own geometry | **reject + repair** |
| V02 | Grand total | equals the sum of component weights | **reject** |
| V03 | Mandatory set | the family's required components are all present | **reject** |
| V04 | Phantom bottom | U-panel has **no** bottom panel | **reject** |
| V05 | Phantom RF | corner-loop bags have **no** reinforcement fabric | **reject** |
| V06 | Side panels | u_panel has exactly 2; circular and 4-panel have 0 | **reject** |
| V07 | Tie presence | FS, DS or Skirt present ⇒ a tie exists | **reject** |
| V08 | Rope ≠ tie | a ROPE row is never counted as a TIE | **reject** |
| V09 | Belt capacity | `GPM × 35 × qty × legs ≥ SWL × SF` | **reject** |
| V10 | Belt width band | inside the band for the loop type (§1.5) | **reject** |
| V11 | Spout cut | `= D × 3.14 + 12` | **reject + repair** |
| V12 | Spout width | `= H + 5` (FS) or `H + 8` (DS), plus closure extra | **reject + repair** |
| V13 | Iris tie | `= D × 3.14 + 38`, 2 pieces | **reject + repair** |
| V14 | Baffle qty | exactly 4 when family is baffle | **reject** |
| V15 | GSM catalogue | body GSM is a value the plant actually weaves | **reject** |
| V16 | GSM vs chart | below the band **and** the customer did not state it | **reject** |
| V17 | GSM vs chart | below the band **and** the customer stated it (C6) | ⚠ **warn + clarify** |
| V18 | Weight vs target | outside ±2% of `PO × 0.99` | ⚠ **warn + clarify** |
| V19 | Safety factor | 5:1 is single-trip only; 6:1 for multi-trip / UN | ⚠ warn if reuse implied |
| V20 | Static type | Type A only for non-flammable; Type C must be groundable | ⚠ warn if the product suggests otherwise |
| V21 | Line-level diff | every line compared against the nearest retrieved bag | advisory |

**Presentation requirement (H5).** The output must lead with **construction type**, then **bag weight and GSM**, then everything else. Asked what he would check to trust a generated BOM in ten seconds, the engineer said: *"first and foremost the bag construction type… if the bag type is chosen correctly then the weight of the bag along with the GSM taken."* That ordering is a requirement, not a preference.

---
---

# 8 · Data pipeline

## 8.1 The source problem, and its answer

Not every BOM has a matching customer query on disk. It does not matter: **every BOM sheet contains its own enquiry, in the header block.** Before doing any engineering, the engineer transcribes what the customer asked into `A3:C11` and `G3:L11`. That header *is* the customer's request, already normalised by a human. All 395 sheets have one.

| Asset | Count | Use |
|---|---|---|
| BOM sheets with a component table | **395** | Source of all four gold layers |
| `SPEC JIEXP-0xx.pdf` — real customer TDS | 6 | **eval only, never train** |
| `COMPONENT C2x SPEC.PDF` | 7 | vocabulary + eval |
| Scanned enquiries (`img*.pdf`, `Image*.pdf`, `*.jpg`) | ~9 | OCR, hand-label, eval |
| Raw WhatsApp / email enquiries | **0** | the gap — see §12 |

## 8.2 The four gold layers — `tools/build_gold.py`

```
for each BOM sheet:

  OrderSpec_gold      ← HEADER BLOCK ONLY
                        A3:C11  customer · order · ref · SWL · SF · qty · bag type
                                · colour · BAG WT. / REQ. WT.
                        G3:L11  printing · ext size · int size · loop · top
                                · bottom · doc · liner · packing
                        // NOTHING from the component table. This is the firewall.

  BuildSpec_gold      ← header + component table + INSTRACTION + tape/loom blocks
                        family      ← taxonomy(bag_type_raw)
                        body_gsm    ← component "BODY PANEL".gsm
                        belt_gpm    ← component "LOOP".gsm
                        loop_*      ← parse header "4X25 · LL 60 CM · SL 40 CM"
                        has_*       ← component row present AND weight > 0
                        dust_proof  ← DDP row + FELT row + instruction lines
                        stitch/fold ← INSTRACTION lines
                        rm_blend    ← MIXING line

  PhysicalBOM_gold    ← component table verbatim, qty recovered by reconciling
                        recorded weight against unit weight
                        // renderer tests ONLY. Never a training target.

  Clarification_gold  ← for each OrderSpec field with state=not_specified,
                        emit the question the rule book says is needed
                        // ~395 rows, zero labelling effort
```

**The firewall is structural, not procedural.** `build_order_spec()` receives only the header cell range and physically cannot see the rest of the sheet. `tests/test_firewall.py` asserts that every OrderSpec field traces to a header cell, and fails the build if not.

**Ingest repairs** applied while building the gold layers:

- `175+30 UNLAMINATED` → laminated (C8, clerical error)
- `SL 730` → `SL 78` (p.8, typo)
- strip `box J fold` and `top hemming` — they do not exist at Anjani (F4)
- flag sheets whose U-panel body cut used `+10` as `historical_variant`
- flag DDP rows whose cut was recorded in cm rather than metres

## 8.3 Dedupe and split — `tools/dedupe.py`, `tools/split.py`

```
1. Content-hash every workbook FIRST.                                   [E, H1]
   DOMESTIC ENQUIRY.xlsx  appears in 2 locations (81 + 59 sheets)
   EXPORT ENQUIRY.xlsx    appears in 3 locations (33 + 44 + 31 sheets)
   "Do not learn from duplicates."

2. Collapse exact duplicate (input, output) pairs to one row.

3. Fingerprint each record:
   sha1(family | ext_L | ext_W | ext_H | swl | sf | top_type | bottom_type
        | req_weight | product_contents)

4. Split the FINGERPRINT GROUPS, never the rows — stratified by family.
   train 70% · val 15% · test 15%

5. Assert zero leakage as a build-failing test:
   assert not (set(train.fingerprints) & set(val.fingerprints))
```

The previous dataset split by workbook — the right instinct — and still leaked **49%** of validation rows verbatim, because the same enquiry file exists three times under different paths. Fingerprint grouping is what actually fixes it.

## 8.4 Training data

| Adapter | Rows | Source | Effort |
|---|---|---|---|
| **A — extraction** | ~1,300 verified synthetic | enquiry prose rendered from `OrderSpec_gold`, **round-trip verified** | 3 days |
| | ~200 hard negatives | hand-built: two size triples in one sentence, negations, imperial units, TDS style, `Ø 40 CM × 50 CM HEIGHT` | 1 day |
| | **~30 real — EVAL ONLY** | SPEC JIEXP PDFs, COMPONENT sheets, OCR'd scans | 1 day |
| **B — configuration** | **395 real** | `OrderSpec_gold` + retrieved + envelope → `BuildSpec_gold` | **zero** |
| | ~1,200 solver-feedback | perturb **loop GPM first, then GSM** — the engineer's knob order — render, train it back | 1 day |
| | ~200 conflict cases | target vs stated GSM contradictions → correct output is a clarification, not a build | 1 day |
| **C — clarification** | ~395 | derived from which OrderSpec fields were absent | **zero** |

**Synthesis rules for adapter A** — `tools/build_extractor_set.py`:

```
for each OrderSpec_gold:
  for style in [whatsapp_en, whatsapp_hinglish, email_formal, tds_table, phone_notes]:

    1. DROP fields at the rates measured in the corpus, so the synthetic
       enquiry is as incomplete as a real one:
         liner absent 78.5% · doc pocket 44.6% · printing 43.0%
         packing 17.0%      · bag weight 9.1%  · SWL 0.8%

    2. RENDER the surviving fields into prose. Inject the real noise:
         PANNEL · CLOUSER · CIRCULAR NAG · LOOPBAFFLE (no space) · APNNEL
         gr/m2 · 3" · 5:01 · 6:01/UN · 2.5kg / 2500 gm / 2.5 KGS

    3. VERIFY — re-extract from the generated text, compare field by field
       against the OrderSpec it came from.
         identical    → KEEP
         any mismatch → DISCARD. Do not repair. Do not ship.

    4. NEVER render from BuildSpec_gold. The customer did not choose the belt
       gramage; putting it in the enquiry teaches the extractor to read a
       field that will never be there.
```

Expected yield after verification: 60–70%.

**Adapter C** is small enough to fold into adapter B as a second output field rather than a third LoRA. Decide after measuring.

---
---

# 9 · Fine-tuning

## 9.1 Why two adapters

Both are LoRA on one shared `Qwen3-4B-Instruct` base, loaded side by side. The reason to split is not cost — it is that **they are trained to do opposite things**.

| | Adapter A — extraction | Adapter B — configuration |
|---|---|---|
| Job | read what was said | decide what was not said |
| Correct behaviour on a missing field | emit `not_specified` | fill it in from experience |
| Worst failure | asserting a value the source does not contain | leaving a field null and stalling the renderer |
| Primary metric | **hallucination rate < 2%** | per-field accuracy vs the engineer's actual choice |
| Checkable against source? | **yes** — the evidence span exists or it does not | no — only against what was historically built |
| Retrain trigger | new customer vocabulary, new document format | rule change, new family, practice shifts |

Train one model on both and you teach it that filling blanks is sometimes right and sometimes forbidden, with nothing in the input to distinguish the cases. The hallucination metric — the one number that decides whether this is safe in front of a customer — becomes unmeasurable.

## 9.2 Configuration

| Setting | Adapter A | Adapter B |
|---|---|---|
| base | `Qwen3-4B-Instruct` (Apache 2.0) | same |
| method | **LoRA, bf16** — not QLoRA; at 4B the saving is unnecessary and 16-bit train/serve parity preserves accuracy | same |
| rank `r` | 16 | 32 |
| `lora_alpha` | 32 | 64 |
| `lora_dropout` | 0.05 | 0.05 |
| target modules | `q_proj k_proj v_proj o_proj gate_proj up_proj down_proj` | same |
| learning rate | 2e-4 | 1e-4 |
| scheduler | cosine, `warmup_ratio 0.03` | same |
| epochs | 2 | 3 |
| batch | `per_device 2`, `grad_accum 4` → effective 8 | same |
| `max_seq_length` | 2048 | **4096** — three retrieved BuildSpecs in the prompt |
| loss | completion-only, prompt masked | same |
| eval | every 50 steps, early stop on eval loss | same |
| tooling | Unsloth (~1.5–2× faster, ~50% less VRAM than stock FA2) | same |
| wall clock | under an hour | under an hour |

Watch training loss settle in the **0.5–1.0** band. Approaching zero means it has memorised the fingerprints — check eval loss, cut epochs or rank.

## 9.3 Serving — the grammar matters more than the fine-tune

Serve under **vLLM with XGrammar**, passing the JSON Schema generated from the Pydantic model as `guided_json`. Sub-40 µs per token, effectively free.

Encode as much as possible into the schema rather than checking after:

```
body_gsm      : enum[65,70,75,80,85,90,95,100,103,105,110,120,122,125,130,135,
                     140,143,145,150,155,160,165,170,175,180,185,190,195,200,
                     205,210,215,220,225,230,240,245,260,370]
belt_width_mm : enum[40,45,50,60,70,72,75,80,100]
belt_gpm      : enum[22,25,28,30,32,35,40,42,45,50,55,60,65]
family        : enum[u_panel, circular, four_panel, four_panel_baffle, two_panel,
                     single_loop, two_loop, omega, tunnel, tubular, h_bottom,
                     container_liner]
loop_qty      : enum[1,2,4]
static_type   : enum[A,B,C,D]
dust_proof    : enum[NONE, SINGLE, DOUBLE, TRIPLE]
liner_insertion : enum[LOOSE, TABBED_4, TABBED_8, GLUED, HEMMED]
fold_spec     : enum[OUT_FOLD, J_FOLD]        // "box J fold" cannot be emitted
stitch_spec   : enum[OVERLOCK_CHAIN, DOUBLE_CHAIN, DOUBLE_NEEDLE]

// What the grammar CANNOT express — the gate must still check:
//   body_gsm >= envelope.gsm_min        (depends on this order's SWL/SF)
//   belt_gpm inside envelope.belt_band  (depends on this order's load)
//   mandatory component set for family  (depends on the chosen family)
// Defence in depth: grammar for form, gate for consistency.
```

---
---

# 10 · Evaluation and acceptance gates

## 10.1 Four held-out sets

| Set | n | Purpose |
|---|---|---|
| `eval_clean` | ~60 | in-distribution, no integrity flags |
| `eval_hard` | ~30 | missing SWL or bag weight, unusual families, accessory-heavy |
| `eval_real` | ~30 | hand-labelled real PDFs and scans. **Never trained on. The only set that measures the actual job.** |
| `eval_regression` | 20 | fixed cases incl. 85×85×85. **Must never regress.** |

## 10.2 Ship gates

| Layer | Metric | Gate |
|---|---|---|
| Renderer | replay all 395 sheets, `BuildSpec_gold` → `PhysicalBOM_gold` | **≥ 95% of lines within 1%**, and 100% of loop lines exact |
| Adapter A | **hallucination rate** — fields whose evidence span is absent from the source | **< 2%** on `eval_real` |
| | exact match on numerics (dims, SWL, SF, spout, micron) | > 95% |
| | accuracy on enums (family, top, bottom, closure) | > 92% |
| | F1 on booleans (liner, baffle, doc pocket, printing) | > 0.95 |
| Adapter B | body GSM exact match | > 55% |
| | body GSM within one catalogue step | > 85% |
| | component set F1 | > 0.96 |
| End to end | median bag-weight error vs `PO × 0.99` | **< 2%** |
| | share inside ±2% | **> 70%** |
| | geometry within 2 cm of what was actually cut | > 90% per component |
| | **GSM floor violations with no customer override** | **zero, always** |
| Safety | conflict cases routed to clarification, not silently built | **100%** |
| | solver converges within 3 passes | > 90% |

## 10.3 Four baselines that must be beaten

1. The deterministic rule engine alone, no model anywhere.
2. Rule engine + retrieval fusion, still no model.
3. **Base `Qwen3-4B`, no fine-tuning, few-shot with 8 examples, under the same grammar.** Run this in week one — it costs nothing and is often startlingly close.
4. The current regex normaliser, for adapter A specifically.

Measure each rule change **on its own, first**. If you change the target-weight rule and the fine-tune at the same time, the attribution is lost permanently.

---
---

# 11 · Build schedule

Nothing before phase 6 needs a GPU. Phases 1–4 alone should take median weight error under 3%.

| Phase | Work | Exit criteria | Days |
|---|---|---|---|
| **1** | **Rule registry.** Every rule in §1 becomes JSON with `rule_id`, `rule_level`, `source`, `agreement`. The four open items go in flagged `needs_confirmation` and **fail loudly** rather than silently picking a side. | `rules/loader.py` loads all 11 files; `test_geometry.py` reproduces every stated agreement figure | 2 |
| **2** | **Renderer.** Geometry, quantities, weights, spouts, loops, yarn, DDP, assembly. Replay all 395 sheets. | ≥ 95% of lines within 1% of `PhysicalBOM_gold`; 100% of loop lines exact; 85×85×85 reproduces to 876.6 g | 5 |
| **3** | **Classifier, SWL derivation, envelope.** Deterministic family/loop/top rules. Digitise the National Bulk Bag density table (28 pp: name, lbs/ft³, g/cm³). GSM and belt bands from the corrected charts. | family classification ≥ 98% against `BuildSpec_gold`; density lookup covers ≥ 500 products | 3 |
| **4** | **Solver + clarification engine.** Both modes. Knob order loop GPM → loop cut → body GSM. Target = PO × 0.99, ±2%. The conflict path that emits two builds and a question. | median weight error < 3% on the 350 sheets stating a bag weight; 100% of constructed conflict cases produce a clarification | 4 |
| **5** | **Gold layers, firewall, dedupe, split.** | `test_firewall.py` and `test_no_leakage.py` both pass; 395 OrderSpec + BuildSpec + PhysicalBOM + Clarification rows written | 4 |
| **6** | **Adapter B.** Its data is already real and complete. Generate solver-feedback and conflict rows, train, serve under grammar, measure against baselines 1 and 2. | beats baselines 1 and 2 on body GSM and component F1 | 3 |
| **7** | **Adapter A.** Round-trip-verified synthesis, 200 hard negatives, ~30 real documents hand-labelled into `eval_real`. Train, serve, gate hard on hallucination rate. Keep the regex path as automatic fallback. | hallucination < 2% on `eval_real`; beats the regex baseline on every field group | 5 |
| **8** | **Output writer and audit.** Four-block sheet, **construction type first**, then weight and GSM. Per-field provenance. Clarification list as a co-equal deliverable. | an engineer can trace any field to a rule ID, a neighbour, or the model, in one click | 3 |
| **9** | **Shadow run.** Generate a BOM for every real enquiry alongside the engineer, without showing him until he has finished his own. | 30 consecutive enquiries with ≤ 2 substantive disagreements | 1 month |

**Total to shadow run: ~29 working days.**

---
---

# 12 · Open items and risks

## 12.1 Open items — five short questions

| # | Item | Why it matters | Interim handling |
|---|---|---|---|
| **O1** | **The U+2 GSM chart.** He said "we will prepare a fresh one." It does not exist yet. | U-panel is 44% of all bags. FORWARD mode cannot run for it without a chart. | Use the 4-panel-baffle **corner-loop** column as the interim floor (140 GSM at 751–1000 / 5:1) and label every U-panel forward-mode output `INTERIM CHART`. |
| **O2** | **Belt strength sheet** (D5) and **liner cut-size formula** (E7) — both referred to as "already shared", neither is in this folder. | V09 cannot be finalised; liner cut sizes are guessed. | V09 runs at `warn` until the sheet arrives. Liner cut = customer-stated only. |
| **O3** | **Belt legs.** `GPM × 35 × 4 ≥ SWL × SF` holds on only 39% of sheets. With ×2 legs it holds broadly. | V09 severity depends on this. | Implement `legs = 2` with a config flag; log every sheet that fails at `legs = 1`. |
| **O4** | **Single-loop yarn coefficient.** `0.25 × H` gives 64% median error on 14 sheets — far worse than every other family. | Only 14 bags, but the coefficient is clearly wrong. | Use the measured median (25 g flat) and flag. |
| **O5** | **Lamination band edges.** The table is 64.4% exact; misses cluster at base 60–65 (used 20, table says 15) and base 155–170 (used 25, table says 30). | Affects every laminated component. | Implement as given, log deviations, revisit after phase 3 with measured bands. |

## 12.2 Risks

| Risk | Mitigation |
|---|---|
| **The firewall leaks** — a BuildSpec field reaches `OrderSpec_gold` | Structural, not procedural: the builder function cannot see the component table. Plus `test_firewall.py` asserting OrderSpec fields ⊆ header cells, failing the build. |
| **Synthetic enquiries teach paraphrase artefacts** rather than FIBC vocabulary | Machine-verify every row by round-trip. Cap synthetic at ~70% of the set. Gate on `eval_real`, never on `eval_clean`. |
| **Model breaks the GSM floor** with no customer override | Four independent layers: the 200 conflict training rows, the envelope in the prompt, validator V16, and a hard assertion in the writer. |
| **Solver oscillates** | Pass history in the feedback so the model sees what it already tried; cap at 3; fall back to the deterministic inversion if it has not converged. |
| **Engineer's rules diverge further from history** | His answer is always the rule; the divergent sheets get an `integrity_flag` and are excluded from geometry regression. Record the disagreement in the registry — never silently pick a side. The +8/+10 case is the template. |
| **Nobody retrains it** | Both adapters retrain in under an hour. Script them as `tools/train_a.py` / `tools/train_b.py` next to `build_gold.py`, run whenever the corpus grows. |
| **Rule tables drift from the model** | Adapter A extracts customer intent only and encodes no rule tables, so registry edits never invalidate it. Adapter B sees the envelope as *input* rather than memorising it, so a chart change is a data change, not a retrain. |

## 12.3 The one thing to start today

**Keep the raw enquiries.** Every WhatsApp message, forwarded email, photographed spec sheet and scanned TDS, exactly as received, filed against the order number it became. He agreed to try for the next twenty. Twenty real ones are worth more than a thousand synthesised, and every week that passes without collecting them is a week of the only training data that cannot be reconstructed.

---
---

# 13 · Rules from the engineer's notebook

**Source:** ~60 pages of the engineer's own handwritten training notebook (IMG-20260804-WA0021 → WA0084), transcribed. This is teaching material he wrote for himself, not a reply to a questionnaire — which makes it the most candid source in the project. It **resolves two open items outright**, adds geometry for **eight more families**, and supplies the plant-floor formulas (tape, loom, needle-loom, stitching) that were previously blank.

## 13.1 Two open items now closed

### O3 — belt gramage. RESOLVED. [notebook p.107]

```
required_GPM = (SWL × SF) / (loop_qty × 35)

worked example from the notebook, verbatim:
  1000 kg / 6:1 bag
  => 1000 × 6      = 6000 kg
  => 6000 / 4      = 1500 kg per loop
  => 1500 / 35     = 42.8 gram
  => "Approxly 40-45 gram loop"
```

There is **no leg factor**. It is a straight divide by the number of loops. He also notes: *"per gram 35 kg at some companies, 40 kg at others"* — Anjani uses **35**.

> **Corpus check (n=321):** median deviation from the required figure **16%**; only **45%** of bags sit at or above it. This is a **design target the engineer rounds to an available belt**, not a hard limit. **V09 therefore becomes a WARNING, not a reject.** That is a change from §7 and it matters — as a hard gate it would have rejected more than half of Anjani's own production history.

### O2 — liner cut size. RESOLVED. [notebook p.86]

```
liner_width  = 2 × W + 5
liner_length = bag_height + skirt_height + (W / 2)          ← for the bottom
                          + bottom_spout_height + 10        ← knotting
                          + 5                               ← hemming

worked example: bag 95 × 95 × 125 (ID), skirt 80, D/S 40×50
  width  = 95 + 95 + 5 = 195 cm
  length = 125 + 80 + 47.5 + 50 + 10 + 5 = 317.5 cm
  liner  = 195 × 317 cm

allowances:  hemming +5 cm   knotting +10 cm   cutting 15 cm (per customer)
weight:      micron × length × width × 2 × 0.92 / 10000     ← confirms W3 exactly
```

### Governing standard — also closed [notebook, "UV also STD"]

`ISO 21898` confirmed in his own notes, alongside `ASTM 154-G` for UV. The "need to check" mark on the rules PDF is superseded. **The output may now cite ISO 21898.**

## 13.2 Baffle geometry — now fully specified

Three formulas that were guesses are now exact, and one is a **correction to B2**.

```
!! BAFFLE GEOMETRY USES INTERNAL DIMENSIONS, NOT EXTERNAL          [p.61, verbatim]
   "Baffle Bag width and cut length calculation decide always internal Bag
    Dimention. Not decide outer Bag Dimention. Imp."

corner baffle panel width = sqrt( (L_int/3)² + (W_int/3)² ) + 7        [p.59]
                            ← Pythagoras across the corner triangle
center baffle panel width = W_int + 7                                   [p.60]
baffle cut length         = H_int − 20                                  [p.60]
                            ← 10 cm down from top, 10 cm up from bottom

baffle FABRIC width       = W_int + 12                                  [p.67]
   marked as   (W/3 + 6) | W/3 | (W/3 + 6)
   e.g. 90 wide  →  36 | 30 | 36   = 102 = 90 + 12
        96 wide  →  38 | 32 | 38   = 108 = 96 + 12    ← the "108" from the rules PDF
   the +6 at each edge is the folding allowance
```

| Rule | Corpus check |
|---|---|
| corner baffle width `√((L/3)²+(W/3)²) + 7` | **93% within 3 cm** (n=68) |
| baffle cut `H_int − 20` | 56% exact, 62% within 3 cm (n=68) — the +4/+5 residuals are bags stitched 8 cm rather than 10 cm from the edge |
| baffle fabric width `W + 12` | reproduces the 108 cm figure from the rules PDF exactly |

**Baffle punching waste** [p.67] — a real component that was missing entirely:

```
punch patch = 10 cm punched through, 10 cm unpunched, 30 cm standard width
punch_waste_g = GSM × 10 × 30 × (holes_per_baffle × 4 baffles) / 10000

example: 130 gsm (20+90+20), 4 holes per baffle
  => 130 × 10 × 30 / 10000 = 3.9 g per patch
  => 3.9 × 16 = 62.4 g per bag
```

**Baffle stitching patterns** [p.61] — four, and the choice is a BuildSpec field:
`4_BAFFLE` · `CENTER_BAFFLE` · `2_BAFFLE` · `2_BAFFLE_PLUS_CENTER`
Punching is `NORMAL` (manual) or `OVAL` (machine).

## 13.3 Spouts and closures — refined

The notebook is more precise than the rules PDF on three points.

```
cut length = DIA × 3.14 + 12    (single fold)                          [p.99]
           = DIA × 3.14 + 15    (double fold)     ← NEW, not in the rules PDF

FS width   = height + 5                                                [p.99]
DS width   = height + 5 + 3 hemming = height + 8    ← explains WHY it is +8

IRIS   width = height + DIA/2 + 6 (iris hemming) + 5 (stitching)       [p.99]
             = H + D/2 + 11 , then rounded up to a stock width
             worked example: 50 + 20 + 6 + 5 = 81  →  "approxly 85 le lete hain"
       tie   = DIA × 3.14 + 38                     ← CONFIRMS the rules PDF  [p.103]

PETAL  width = height + 5 + 3 hemming = H + 8      ← same as a normal DS  [p.16]
       flap  = DIA / 1.42   →  40/1.42 = 28.16 cm, cut as 30 × 30 cm  [p.103]

PYJAMA width = spout height + 2 × (DIA/2) + 2 × 5 stitching fold        [p.16]
             = H + D + 10
             worked example: 50 + 40 + 10 = 100 cm
             (spout + iris + iris = three layers)
```

> **Corpus check on the iris width:** the `H + D/2 + 11` core is **exact** on D40/H50 (81 cm), but only 52% of sheets land within 2.5 cm once rounded — actuals cluster hard on 85 and 95. The formula is right; the **rounding convention needs one sentence from him** (open item O6).

**Round and cross punch** [p.104] — new, and needed for any spouted bag:

```
round punch  = DIA − 5      (2.5 cm inside the fabric on each side)
cross punch  = DIA − 2.5
round patch weight = 3.14 × r² × GSM / 10000       [p.19, p.104]
   example: DIA 40 → round 35 → r 17.5 → 3.14 × 306.25 = 961.6 cm²
            961.6 × 170 gsm / 10000 = 16.35 g
```

## 13.4 Skirt / duffle — now exact [p.101]

```
skirt_width  = W/2 + 15 (knotting) + W/4 (stitching from edge) + 5 (folding)
skirt_length = W × 4 + 12

worked example: 90 × 90 × 130 (ID)
  width  = 45 + 15 + 22.5 + 5 = 87.5   →  "normally 85 cm skirt use"
  length = 360 + 12 = 372
  size   = 85 × 372 (ID)  |  85 × 360 (OD)

Note: on a circular bag ID and OD are the same size; the skirt is always taken on ID.
```

Corpus (n=54): width residual clusters at −3 to +4 cm; length exact on 37%, +9/+16 next.

## 13.5 Eight more families — geometry supplied

The engineer's own family list [p.57] is: U+2 / 4-panel · Q-bag (baffle) · circular (cross corner) · pinch corner · tunnel · drum · omega · platten · hood (I-bag) · container. With the notebook, eight of these now have real formulas.

| Family | Body | Side / other | Source |
|---|---|---|---|
| **Box type** | `(W+8) × (2H + L + 8)` | side `(L+8) × (H+8)` | p.71 — **identical to U-panel**, reuse the block verbatim |
| **Two-panel (C-type)** | side panel `(2W + 12) × (H + 12)`, qty 2 — built as half + full + half panel, seam at bag centre | cross-corner loop | p.74 |
| **Omega** | width `2W`, cut `H + 5 + omega + omega + 2.5` | top / bottom `(W+10) × (W+10)`; omega height per customer, default 15 cm; loop stitched double chain, 3 times | p.67 |
| **Hood (I-Bag)** | width `W + 7`, cut `L/2 + H + 2×hood_height + H + L/2 + 7` | side `(L+7) × (H+4)`; **no lifting loop** — the hood *is* the lift; bottom cut from body fabric, U or V sleeve | p.69 |
| **Pinch corner** | tubular `(W+L) × (H+12)` | top / bottom `(W+12) × (W+12)`; plain circular fabric, **no RF** | p.63 |
| **Circular cross corner** | tubular `(W+L) × (H+12)` on ID | top / bottom `(W+10) × (W+10)` | p.63 |
| **Platten (sling)** | bottom only `(W+8) × (W+8)` | full-loop pattern attached; no side panels | p.68 |
| **Container liner** | width `W + 16` (double fold), cut `2L + 2H + 16` | side `(H+16) × (L+16)`; yarn flat 300 g (40 ft) / 150 g (20 ft) | p.10 |
| **Conical** | 4-panel body | conical plate: spout flat = `DIA × 3.14`, divided into 4 parts, `+8` folding each; conical height given in **diagonal** — solve the other side by Pythagoras | p.72, p.73 |
| **Tunnel** | — | side `(W+7) × (H+7)` — note **+7**, not +8 | p.65 |

> **A conflict to resolve (O7).** The notebook consistently gives circular body cut as `H(ID) + 12` [p.63]; the rules PDF signs off `H(ext) + 8`. If external = internal + 4 these are the *same number* — but he also stated in B5 that for circular bags ID and OD are equal, which makes them differ by 4 cm. Weight impact ≈ 14 g on a 2 kg bag (0.7%). Implement `H + 8` on external (his signed ruling, and the corpus mode at 52%); log every case.

## 13.6 Stitching — the real formula [p.99, p.95, p.93]

This replaces the yarn coefficient as the *precise* method; the coefficient stays as the fast default.

```
thread_wt = stitching_path_length_cm × stitches_per_cm × thread_DNR / 9000
oil absorption: ADD 18% to the total thread cut          [p.95, "y.Imp Note"]

stitching path is summed per seam type, e.g. for 90×90×125 with FS 40×50, DS 35×50:
   HR  680 cm   DR  680 cm   TOP  90×4 = 360   FS  125×2 = 250
   DS  110×2 = 220          DS hemming 110                  total 2190 cm
```

**Machine table** [p.91, p.92, p.93] — a BuildSpec enum, and it drives the thread figures:

| Machine | Model | Needle | Guide | Stitches / 10 cm | Thread | Seam strength |
|---|---|---|---|---|---|---|
| **DR** (safety) | ST-603 DR | 28, 29 | 20 mm | 12 | 3500 DNR PP | 200–250 kg (max 208) |
| **HR** (Heracle, overlock) | ST-602 HR | 82 | 15–17 mm | 10 | 8500 DNR PP | 250–300 kg (305) |
| **DDR** (double needle) | ST-605 SUF | — | — | — | — | — |
| **VMC** (round) | — | 26–27 | 25 mm | 18–19 | as DR | — |
| **UDDR** | ST-603 UDR | — | — | — | — | — |
| **Jukki** (lock stitch) | — | 23, 24 | — | 13–14 | 1100 × 2 = 2200 DNR | — |

**Jukki loop-attachment thread** [p.93] — a real BOM line that was missing:

```
jukki_thread_g = 0.0833 × passes × attachment_length_cm      (0.5 g per 6 pass per cm)

  6 pass × 30 cm = 15.0 g       6 pass × 35 cm = 17.5 g       8 pass × 30 cm = 20.0 g

PASS COUNT by load:
  SWL 1000 / 5:1  →  6 pass          SWL 1200 / 5:1  →  6 pass
  SWL 1000 / 6:1  →  6 pass          SWL 1250 / 5:1  →  6 pass
  from SWL 1200 / 6:1 and above      →  8 pass
```

Yarn types [p.95]: PP (polypropylene) · MF (multifilament) · fabricated yarn. Jukki yarn: PP or polyester.

## 13.7 Reinforcement fabric (RF) [p.15, p.16]

```
RF tape count = RF_width_cm × 2 × 2.54 × mesh          (per RF strip)
RF weight     ≈ 11% of the body fabric weight

worked example: 180 cm tube, 180 gsm, RF 10 cm
  body fabric wt = 180 gsm × 180 cm × 100 cm × 2 / 10000 = 648 g
  RF wt          = 72 g
  RF percentage  = 72 / 648 = 11.11%
```

RF is warp-direction double tape from one loom. **It applies to cross-corner constructions only** — the rules PDF already establishes that corner-loop bags carry no RF.

## 13.8 Plant-floor formulas — for the tape / loom / needle-loom block

These make the third block of the BOM sheet generatable rather than hand-filled.

```
TAPE PLANT                                                          [p.1, p.13]
  DNR  = GSM × 9000 / ((warp_mesh + weft_mesh) × 39.37)
         example: 104.4 × 9000 / (22 × 39.37) = 1084.8 DNR
  GPD  = strength_g × 1000 / DNR          (tenacity)
         example: 9 / 1500 × 1000 = 6
  tape strength = GPD × DNR               example: 6 × 1500 = 9000 g = 9 kg
  elongation %  = increase_in_length × 100 / initial_length
                  required standard for jumbo: 18–20%
  tape production = line_speed × no_of_tapes × DNR / 150000          [p.3]
  Lohia plant: 7.5 MT/day = 225 MT/month, wastage 2%, die 1000–1100 mm

LOOM                                                            [p.14, p.17, p.10]
  no_of_tape (flat) = fabric_width_cm × 0.394 × mesh
  no_of_tape (tube) = fabric_width_cm × 2 × 0.394 × mesh
  no_of_tape        = fabric_width / tape_width          (cross-check)
  ring size         = fabric_size × 2 / 3.14
  mesh              = tapes per inch; warp = creel, weft = shuttle

  loom capability:
    LSL-6    20 coil × 36 group = 720 tape → 72" tube → 36" flat    min 12"
    ACE-6    8×2 × 36 group     = 576 tape → 57.6" tube → 28.8" flat
    LSL-620  18×2 × 36 group
    LSL-8    20×2×56 = 2240 tape + 250 extra for the RF line   min 64", max 85"

NEEDLE LOOM (webbing)                                          [p.106, p.108, p.109]
  production = belt_gram × RPM × 60 × hours     e.g. 40 × 2.3 × 60 × 10 = 55.2 kg/head
               4 heads per machine → ~160–220 kg/machine/shift
  group      = loop_width_mm / reed_size_mm     reed sizes 1.5, 2.0, 2.2 mm
               50 mm / 1.5 = 33 group      75 mm / 1.5 = 50 group
               100 mm / 2.0 = 50 group     30 mm / 1.5 = 20 group
  tape DNR   : 7000 DNR = 1 gram (including wrapping yarn)
               50 g belt at 50 group → 1750 DNR tape
  loop strength = belt_gram × 35 kg      e.g. 50 g → 1750 kgF minimum
```

## 13.9 Catalogues the notebook supplies

**Nine fabric types** [p.56] — a BuildSpec enum, currently missing:
`NORMAL` · `ANTISTATIC` (Type B) · `CONDUCTIVE` (Type C) · `DISSIPATIVE` (Type D) · `EXTRA_UV` · `NET` (mosquito) · `BREATHABLE` (low mesh) · `VENTILATED` (vents + both-edge warp double tape 10 cm from edge) · `SANDWICH` (two fabrics joined by centre lamination, e.g. 170 + 30 coating + 70)

**Five liner types** [p.81] and **two insertion methods** [p.63]:
`STANDARD` (PE hose, wrinkled) · `FORM_FIT` (bottle shape, adjusts at the spout) · `Q_LINER` (PE baffles inside) · `SUSPENDED` (for one-end two-loop bags) · `SHROUD` (cap style)
Insertion: `LOOSE` (default, pre-blowing recommended, most cost-efficient) · `TABBED` (fixed at the eight corners — *"may create problems during filling and discharge"*)

Liner shapes [p.82]: both-side open · bottle top+bottom sealed · top and bottom spout bottle · flange liner (fabric tape attached, sewn with seam).

**Three dust-proof grades** [p.96] — confirms E4 exactly, with the mechanism:
`SDP` single — filter cord one side · `DDP` double — filter cord both sides · `TDP` triple — both sides **plus felt in the centre**
Filler cord: 4.5 g/m, **DIA 7.2 mm**, strength 27–60 kg.

**Hose pipe** [p.103]: 5 cm cut length, **160 g/m**. **Rope** [p.103]: DIA 7–8 mm, PP rope or braided rope.

## 13.10 Type C electrical spec — now precise [p.54]

```
Type C conductive grid:
  maximum mesh size                    50 mm
  if threads run in ONE direction only, spacing < 20 mm
  interconnection resistance           < 10^7 ohm
  breakdown voltage                    ≤ 6 kV      (also the Type B limit)
```

This turns validator **V20 from a vague warning into a checkable rule** whenever the customer specifies Type B or C.

## 13.11 UN testing — the full six [p.36, p.37, p.39, p.41, p.58]

| Test | Parameter |
|---|---|
| Top lift | 6 × max gross mass, held 5 minutes |
| Drop | 1.8 m (PG I) · 1.2 m (PG II) · 0.8 m (PG III) |
| Topple | 1.2 m (PG II) · 0.8 m (PG III) |
| Righting | lifted from its side at 0.1 m/s to upright |
| Stacking | 1.8 × max stacking weight on top, 24 hours |
| Tear | 10 cm knife cut, 2 × max gross load, 5 min lift at 45°; hole must not grow > 25% |
| Compression | 4 × SWL dead load on top, 6 hours |

**UN code** [p.36, p.37]: `13H1` uncoated without liner · `13H2` coated without liner · `13H3` uncoated with liner · `13H4` coated with liner.
Packing group `X` high (1.5 m³, 180 cm drop) · `Y` medium (3.0 m³, 120 cm) · `Z` low (3.0 m³, 80 cm).
Hazard classes carried: 4.1, 4.2, 4.3, 5.1, 5.2, 6.1, 8, 9.

## 13.12 QA constants [p.29, p.32, p.33, p.34, p.39]

```
lab temperature        27 °C ± 2
UV test                200 hrs / 144 hrs ; 8 hr UV at 60 °C then condensation at 50 °C
UV lamp                313 FLB / 313 FLA          standard ISO 21898, ASTM 154-G
ash content %          (crucible_with_ash − empty_crucible) / material_wt × 100
                       example 0.356 / 6.595 = 5.39%
melting points         PP / HDPE 130–180 °C        CaCO₃ (ash) 830 °C
MFI                    PP 230 °C / 2.16 kg at 6 min ; PE 190 °C / 5 min
                       standards ASTM D1238, ISO 1133 ; sample 4–5 g, die ~2 mm
```

## 13.13 What this changes in the build

| Area | Change |
|---|---|
| **§7 validation gate** | **V09 belt capacity moves from `reject` to `warn`.** The corpus shows only 45% of production bags meet the computed target — as a hard gate it would reject more than half of Anjani's own history. |
| **§1.3 geometry** | **Baffle geometry now keys off INTERNAL dimensions.** B2's "everything from external" needs this exception written into `geometry.json` as a per-family `dimension_basis` field. |
| **§1.10 components** | Add `BAFFLE PUNCH WASTE`, `JUKKI THREAD`, `HOSE PIPE`, `ROUND PATCH` as real weighted lines. |
| **§4.2 BuildSpec** | New enums: `fabric_type` (9), `liner_type` (5), `baffle_pattern` (4), `punch_type` (2), `stitch_machine` (6), `jukki_passes`, `fold_mode` (single / double). |
| **§5 renderer** | Eight more family blocks; the punch, jukki and RF lines; the `+15` double-fold spout variant. |
| **§1.12 output** | The tape / loom / needle-loom block is now **fully computable** — DNR, GPD, tape count, ring size, mesh, production rates, group count. It no longer needs to be hand-filled. |
| **§12 open items** | O2 and O3 closed. O6, O7 and O8 opened. |

## 13.14 Revised open items

| # | Item | Status |
|---|---|---|
| ~~O2~~ | Liner cut-size formula | **CLOSED** — p.86 |
| ~~O3~~ | Belt legs | **CLOSED** — no legs; `SWL × SF / (qty × 35)`, and it is a target, not a limit |
| **O1** | The U+2 GSM chart he is preparing | still open — interim: 4-panel corner-loop column, output stamped `INTERIM CHART` |
| **O4** | Single-loop yarn coefficient (`0.25 × H` gives 64% error) | still open — use measured median 25 g |
| **O5** | Lamination band edges (64.4% exact) | still open — implement as given, log deviations |
| **O6** | **NEW.** Iris spout width rounding. `H + D/2 + 11` is exact on D40 (81 cm) but actuals cluster on 85 and 95. What is the rounding rule — nearest stock width, or a fixed uplift? | new |
| **O7** | **NEW.** Circular body cut: notebook says `H(ID) + 12`, rules PDF says `H(ext) + 8`. These agree only if ext = int + 4, but he also said circular ID = OD. Which basis? | new |
| **O8** | **NEW.** Baffle cut `H_int − 20` is exact on 56%; the +4/+5 residuals look like an 8 cm rather than 10 cm stitch-back. Is 10 cm always standard, or does it vary with bag height? | new |

---

## In one paragraph

The BOM agent reads an enquiry in any format and extracts only what the customer actually said, marking everything else `not_specified`. It derives the load from bulk density when the customer gave a product and a volume instead of an SWL. It classifies the construction by fixed rule — U+2 unless a belt of 70 mm or more says circular. A fine-tuned Qwen adapter then makes roughly seventy engineering decisions from a closed vocabulary, informed by the three nearest bags Anjani has actually built and the chart bands for this load. Deterministic code turns those decisions into every number on the sheet: `W + 8` and `2H + L + 8` for a U-panel body, `D × 3.14 + 12` for a spout, `2 × FH + LL + SL` for a loop, `0.45 × H` for the yarn. If the customer named a bag weight, a solver aims at **99% of it** and adjusts loop gramage, then loop cut length, then body GSM until the bag lands within ±2%. A gate of twenty-one checks recomputes every line and refuses anything structurally wrong. And where the enquiry contradicts itself, or the chart, or physics, the agent does not decide alone — it builds both options and hands the engineer the exact question to put to the customer. That last behaviour is the one the engineer asked for by name, and it is what separates a calculator from something worth trusting.

---

*End of implementation plan.*
