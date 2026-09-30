# Anjani FIBC BOM System — Derived Rules & Questions for the Engineer

**Prepared:** 10 August 2026
**Basis:** 107 workbooks / 681 sheets under `All_Things`; **395 sheets carrying a real component table** were parsed with a label-anchored extractor. Every rule below was tested against those 395 sheets. Agreement percentages are **exact-match counts, not curve fits**.
**Scope:** Costing is excluded per instruction. Tape-plant / loom / needle-loom / INSTRACTION blocks are **included**, because they are core BOM, not price.

**How to use this document:**
Part 1 is what the data already tells us — the engineer needs to **confirm or correct** each rule.
Part 2 is what only the engineer can answer — 44 questions, 15 marked **[BLOCKING]**.

---
---

# PART 1 — RULES DERIVED FROM THE DATA

Everything in Part 1 needs a **YES / NO / CORRECTION** from the engineer.

---

## 1.1 Weight formulas

These reproduce exactly across the corpus. Confirm all three.

| # | Applies to | Formula | Status |
|---|---|---|---|
| W1 | Fabric components (panels, spouts, baffle, skirt, top, bottom) | `weight_g = GSM × width_cm × cut_cm × qty / 10000` | Exact on every fabric row tested |
| W2 | Tape / loop / tie / cord / DDP | `weight_g = GPM × cut_cm × qty / 100` | Exact. GPM = grams per metre (linear), **not** g/m² |
| W3 | LDPE liner | `effective_gsm = micron × 1.84` then apply W1 | Derivation: 2 tube walls × LDPE density 0.92 g/cm³ |

> **CONFIRM:** Is W3 correct, and is it always both walls? Does it change for form-fit vs lay-flat vs gusseted liners?

---

## 1.2 Geometry — U-PANEL (U+2)

All dimensions computed from **EXTERNAL** L × W × H. n = 174 sheets.

| Component | Derived rule | Agreement | Notes |
|---|---|---|---|
| Body panel — width | `W + 8` | **163/174 = 94%** | Next values: 9.0 (×3), 47.0 (×3), 4.0, 10.0 |
| Body panel — cut length | `2H + L + 10` | **138/174 = 79%** | `+8` on 12 sheets (7%), `+9` on 6, `+3` on 6, `+5` on 3, `+11` on 2, `+6` on 1 |
| Body panel — qty | `1` | — | U-piece forms bottom + 2 walls |
| Side panel — width | `L + 8` | **156/166 = 94%** | Next: 9.0 (×3), 10.0, 14.0 |
| Side panel — cut length | `H + 8` | **154/166 = 98%** | Next: 7.0 (×6), 10.0, 11.0 |
| Side panel — qty | `2` | **100%** (n=30 resolvable) | |
| Bottom panel | **NONE** | — | U-piece forms the bottom. Do not add one. |
| Reinforcement fabric | **NONE** | — | RF is for cross-corner only |
| Top panel (when fitted) | `(L + 10) × (W + 10)` | 48% mode (n=23) | `+8` and `+12` also appear |

**The +8 / +10 conflict, broken down by customer:**

| Customer | n | Body-cut allowance values observed |
|---|---:|---|
| EXPORT ENQUIRY | 31 | +10 ×29, +12.4 ×1, +25 ×1 |
| PO 28 | 18 | +10 ×18 |
| TECHNOPACK | 12 | +10 ×11, +8 ×1 |
| EXPORT INQUIRY | 11 | +9 ×6, +10 ×2, −28 ×3 |
| DOMESTIC | 8 | +3 ×4, +8 ×3, +6 ×1 |
| JUMBO BAG SPEC | 7 | +10 ×7 |
| DOMESTIC INQUIRY | 5 | +10 ×4, +11 ×1 |
| AIRSON | 4 | +10 ×4 |
| NUDITEX | 4 | +10 ×4 |
| VIJAYNAGAR | 4 | +8 ×3, +10 ×1 |

> **NOTE:** The reference sheet supplied (`90X90X90 CM.xlsx`, contents 85×85×85) uses **+8**: cut 263 = 2(85) + 85 + 8. It is in the 7% minority. See question **B1**.

---

## 1.3 Geometry — CIRCULAR / TUBULAR

n = 104–113 sheets.

| Component | Derived rule | Agreement | Notes |
|---|---|---|---|
| Body — flat woven width | `W + L` (no seam allowance) | mode 38% (n=104) | Comes off the loom as a tube. On 90×90 bags, width − W = 90, i.e. width = 180 = W+L |
| Body — cut length | `H + 8` | **52%** (n=104) | `+10` is the next most common, then +7, +6 |
| Body — qty | `2` (two tube walls) | — | Body implied qty = 2 on 39% of all sheets, matching the circular share |
| Bottom panel | `(L + 10) × (W + 10)` | **86%** (n=94) | Next: +12, +30, +13 |
| Top panel | `(L + 10) × (W + 10)` | **81–82%** (n=68) | Next: +12, +30, +13 |
| Side panel | **NONE** | — | Circular has no side panels |

---

## 1.4 Geometry — 4-PANEL BAFFLE (Q-BAG)

n = 70 sheets.

| Component | Derived rule | Agreement | Notes |
|---|---|---|---|
| Body panel — width | `W + 8` | **64%** (n=70) | Next: +7, +12, −12 |
| Body panel — cut length | `H + 8` | **57%** (n=70) | Next: +7, +10 |
| Body panel — qty | `4` | — | Body implied qty = 4 on 18% of all sheets |
| Bottom panel | `(L + 8) × (W + 8)` | **61% / 59%** (n=70) | Next: +7, +12, +6 |
| Top panel | `(L + 8) × (W + 8)` | **64%** (n=58) | Next: +7, +13, +12 |
| Baffle — qty | `4` | **100%** (n=53) | |
| Baffle — GSM | typically 130, both-side laminated | — | |

**Baffle fabric marking note found verbatim on a production sheet:**
> "BAFFLE FABRIC 108 CM WIDTH, FROM CORNER 38 CM BAFFLE MARK AND BAFFLE TO BAFFLE MARK DISTANCE 32 CM AND LAST BAFFLE MARK TO CORNER DISTANCE 38 CM, ON BAFFLE MARK DOUBLE WARP 2.5 CM. REST ALL FABRIC WITHOUT MARK"

Another instruction line, ×6:
> "4 BAFFLE WITH 80+20 GSM ONE SIDE LAMINATED 10 HOLES AND STITCHING FROM BOTTOM AND TOP 10 CM"

---

## 1.5 Geometry — 4-PANEL (no baffle)

n = 11 sheets. **Too few to be reliable — treat as provisional.**

| Component | Derived rule | Agreement |
|---|---|---|
| Body panel — width | `W + 8` | 55% (n=11) |
| Body panel — cut length | `H + 7` | 55% (n=11) — `+8` next |
| Bottom panel | `(L + 8) × (W + 8)` | 50% / 38% (n=8) |
| Top panel | `(L + 8.5) × (W + 8.5)` | 30% (n=10) — +8, +10, +7.5 also |

---

## 1.6 Lifting loops — SOLVED

**n = 226 testable sheets.**

```
loop_cut_cm = 2 × free_height + LL + SL
loop_qty    = 4
loop_weight = GPM × (cut_cm / 100) × 4
```

**Agreement: 197 / 226 = 87.2% exact match.**

**Header notation:** the loop line reads `4X25 · LL 60 CM · SL 40 CM · white · 50 MM/WHITE`
- `4X25` = **quantity × free height (cm)**
- `LL` = long attachment length
- `SL` = short attachment length

**Worked confirmations:**

| Sheet | qty × FH | LL | SL | Formula gives | Actual cut | Weight check |
|---|---|---:|---:|---:|---:|---|
| 85×85×85 reference | 4×25 | 65 | 35 | 150 | **150** ✓ | 35 g/m × 1.50 m × 4 = **210 g** ✓ |
| DOMESTIC BAFFLE | 4×25 | 60 | 40 | 150 | **150** ✓ | 45 × 1.50 × 4 = **270 g** ✓ |
| CONDUCTIVE BAG | 4×25 | 30 | 30 | 110 | **110** ✓ | 50 × 1.10 × 4 = **220 g** ✓ |
| EXPORT BAG TYPE-1 | 4×30 | 95 | 40 | 195 | **195** ✓ | 40 × 1.95 × 4 = **312 g** ✓ |
| EXPORT BAG TYPE-2 | 4×30 | 95 | 50 | 205 | **205** ✓ | 40 × 2.05 × 4 = **328 g** ✓ |

**Loop quantity:** 4 on **358 / 363 = 99%** of sheets. qty 2 on 5.

**Observed ranges:** free height 22–122 cm, LL 30–140 cm, SL 30–96 cm.

> **IMPORTANT:** The earlier system used `LL + SL + 50` and scored 31% within 2 cm. That was simply the wrong formula. Corner-loop geometry was never the hard problem it appeared to be.

**The 29 misses (13%), for the engineer to explain:**

| File | Sheet | qty | FH | LL | SL | Actual | Formula |
|---|---|---|---|---|---|---|---|
| 105X105X120 CM BAFFLE BAG | 105X105X120 CM B | 4 | 30 | 95 | 65 | 240 | 220 |
| ASHAPURA CHAINA CLAY | 100X100X200 CM B | 4 | 22 | 140 | 730 | 254 | 914 |
| ASHAPURA CHAINA CLAY | 100X100X200 CM U | 4 | 22 | 140 | 80 | 274 | 264 |
| ASHAPURA CHAINA CLAY | 106X106X115 CM | 4 | 25 | 80 | 40 | 255 | 170 |
| DOMESTIC ENQUIRY | SAHYADRI STARCH | 4 | 30 | 90 | 55 | 210 | 205 |
| DOMESTIC ENQUIRY | HONDA BAG WITH L | 2 | 122 | 96 | 96 | 330 | 436 |
| DOMESTIC ENQUIRY | HONDA BAG WITHOUT | 2 | 122 | 96 | 96 | 362 | 436 |
| DOMESTIC ENQUIRY | MADHU SILICA | 4 | 25 | 85 | 40 | 176 | 175 |

Most common residual when it misses (`cut − LL − SL`): 65 cm (×6), 51 (×3), 55 (×3), 135 (×2), 170 (×2).

---

## 1.7 Quantity — it is never written down

**There is no QTY column anywhere in the sheet.** Quantity is only recoverable by dividing the recorded weight by the unit weight implied by the geometry. This is the most fragile step in reading these sheets.

| Component | n | Implied quantity distribution |
|---|---:|---|
| BODY PANEL | 394 | qty1 **43%** · qty2 **39%** · qty4 **18%** |
| SIDE PANEL | 30 | qty2 **100%** |
| BOTTOM PANNEL | 106 | qty1 **97%** · qty2 3% |
| BOTTOM PANEL | 97 | qty1 **82%** · qty2 16% · qty4 1% |
| TOP PANNEL | 131 | qty1 **99%** · qty2 1% |
| TOP PANEL | 65 | qty1 **100%** |
| LOOP | 363 | qty4 **99%** · qty2 1% |
| BAFFLE | 53 | qty4 **100%** |
| BAFFLE FABRIC | 8 | qty4 **100%** |
| FS TIE | 77 | qty1 **94%** · qty2 6% |
| DS TIE | 70 | qty1 **100%** |
| TIE/IRIS ROPE | 57 | qty1 **100%** |
| TIE | 68 | qty1 87% · qty2 10% · qty28 3% |
| **DDP** | 52 | **qty100 92%** · qty10 4% · qty96 2% · qty1 2% ← **ANOMALY, see E3** |
| FILLING SPOUT | 95 | qty1 **100%** |
| D/S | 98 | qty1 **100%** |

Interpretation: body qty1 = U-panel, qty2 = circular (two tube walls), qty4 = 4-panel. **Quantity is a function of family.**

---

## 1.8 Lamination notation

| Notation | Count | Meaning (to confirm) |
|---|---:|---|
| `70+20 LAMINATED` | 184 | base fabric 70 + coating 20 → **GSM column reads 90 (the total)** |
| `LAMI 65+25` | 25 | = 90 total |
| `60+20 GSM` | 25 | = 80 total |
| `145+30 LAMINATED` | 22 | = 175 total |
| `180+30 LAMINATED` | 20 | = 210 |
| `65+20 LAMINATED` | 16 | = 85 |
| `170+30 LAMINATED` | 14 | = 200 |
| `80+20 LAMINATED` | 14 | = 100 |
| `70+20 GSM` | 14 | |
| `60+20 LAMINATED` | 14 | |
| **`175+30 UNLAMINATED`** | **12** | **Contradictory — says a lamination figure then "UNLAMINATED". See C8** |
| `100+20 LAMINATED` | 11 | |
| `120+30 LAMINATED` | 10 | |
| `90+20 LAMINATED` | 10 | |
| `150+30 LAMINATED` | 10 | |
| `65+20` | 9 | |
| **`15+90+15`** | **9** | **Both-side lamination? 15 + 90 + 15 = 120. See C8** |
| `140+25GSM` | 9 | |
| `LAMI 65+20` | 8 | |
| `140+30 BLACK LAMINATION` | 8 | |
| `70+25 LAMINATED` | 8 | |
| `55+15 LAMINATED` | 8 | |
| `65+25` | 8 | |
| `70+20` | 7 | |
| `60+20` | 6 | |

---

## 1.9 Target bag weight is a CONSTRAINT, not an output

**n = 350 sheets stating both a bag weight and a grand total.**

| Metric | Value |
|---|---|
| Median gap between stated weight and component total | **0.67%** |
| Within 1% | **61%** |
| Within 2% | **78%** |
| Within 5% | **91%** |
| Within 10% | **94%** |

**Tolerance stated verbatim on 7 sheets:** `BAG WT +/-2 %`

### GSM predicted by inverting the weight formula against the target

Leave-one-out test, u_panel, n ≈ 279, snapping the prediction to the observed GSM catalogue:

| Predictor | Median err | Exact | Within 5% | Within 10% |
|---|---:|---:|---:|---:|
| Load-chart cell (family, SWL, SF) | 3.33% | 44.7% | 64.7% | 71.3% |
| Same customer + same family | 3.08% | 45.5% | 57.9% | — |
| **`(target_weight − non_panel_mass) ÷ panel_area`** | **0.00%** | **55.6%** | **81.0%** | **89.2%** |

The panel-area formula itself is accurate to **median 0.39%** against what was actually cut (94.7% within 5%).

> **This says the engineer works backward from the required weight, using the load chart only as a floor.** See questions **C2** and **G3**.

---

## 1.10 Stitching / sewing yarn

| Metric | Value |
|---|---|
| `yarn_g ÷ external_H` — median | **0.467** |
| p10 | 0.326 |
| p90 | 0.721 |
| n | 387 |

The commonly-cited rule of thumb is `0.45 × H`, which sits inside this band — but the spread is more than 2×, and the values actually used are **round numbers**, not calculated ones:

| Yarn weight (g) | 22 | 25 | 28 | 30 | 32 | 35 | 38 | 39 | 40 | 42 | 45 | 48 | 50 | 52 | 55 | 60 | 65 | 70 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Count | 6 | 12 | 3 | 15 | 5 | 7 | 2 | 1 | 16 | 15 | 25 | 8 | 13 | 3 | **45** | **62** | **35** | 18 |

> This looks **chosen, not calculated**. See question **F1**.

---

## 1.11 Body GSM catalogue actually woven, by family

These are the only values that appear. A generated BOM must snap to this list.

| Family | n | GSM values observed (× count) |
|---|---:|---|
| **u_panel** | 174 | 75×1, 120×8, **125×35**, 130×7, 135×4, 140×16, 145×4, **150×17**, 155×6, **160×23**, 165×7, 170×2, 180×6, 185×4, 190×3, 195×6, 200×9, 210×4, 220×1, 225×1, 230×2, 240×2, 250×3, 260×2, 370×1 |
| **circular** | 113 | 49×1, 65×2, 71×1, 90×4, 100×1, 103×1, 105×3, 135×2, 143×1, 145×1, 150×3, 155×2, 160×7, 165×8, 170×9, 175×5, 180×3, 185×6, 190×7, 195×9, **200×10**, 205×6, 210×8, 220×2, 230×4, 240×4, 245×3 |
| **baffle** | 70 | 135×1, 155×3, 160×10, 165×6, 170×9, 175×7, **180×12**, 185×2, 190×4, 200×5, 210×5, 230×6 |
| **four_panel** | 11 | 160×1, 165×1, 180×5, 190×1, 195×2, 210×1 |

---

## 1.12 Loop belt — width × GPM combinations observed

| Belt width | GPM values used (× count) |
|---|---|
| **50 MM** | 45×41, 40×37, 30×33, 35×20, 28×16, 32×16, 50×11, 42×10 — **eight gramages at one width** |
| 60 MM | 40×16 |
| 70 MM | 55×6, 50×3, 40×6 |
| 72 MM | 42×4 |
| 75 MM | 50×14, 45×10 |
| 80 MM | 45×15, 55×14, 50×13, 40×7 |

---

## 1.13 The same specification produced different fabric

Taking every group of sheets sharing **family + exact external dimensions + SWL + safety factor**:

- Spec groups with more than one sheet: **108**
- Groups where the chosen body GSM **differs**: **24 (22%)**

| Specification | Body GSM chosen | Who ordered it |
|---|---|---|
| u_panel 90×90×110 · SWL 1000 · 5:1 | **125 · 150 · 210** | AIRSON / AAA / DOMESTIC INQUIRY |
| u_panel 90×90×120 · SWL 1000 · 5:1 | **125 · 130 · 150** | PO 28 / EXPORT ENQUIRY |
| u_panel 90×90×100 · SWL 1000 · 5:1 | **125 · 140** | SPAIN export vs DOMESTIC INQUIRY |
| u_panel 95×95×110 · SWL 1250 · 5:1 | **140 · 145 · 150** | EXPORT BAG TYPE 1 / TYPE 4 |
| u_panel 85×85×90 · SWL 1000 | **140 · 165** | U+2 PANNEL sheets 1 and 2 |
| baffle 105×105×135 · SWL 1000 · 5:1 | **175 · 230** | PUNEET SIR vs PRINTING |
| baffle 110×110×125 · SWL 850 · 5:1 | **175 · 200** | SAHYADRI STARCH vs KAYADARI |
| circular 85×85×129 · SWL 1250 · 5:1 | **165 · 170 · 190** | VINAYKA / VNK / VM RAJASTHAN |
| circular 95×95×134 | **135 · 200 · 210** | DEV SIR / DG KIM-1 / PRINTING |
| circular 90×90×114 | **205 · 230** | SOUTH-1 / SOUTH-2 |

**125 to 210 GSM is a 68% spread on an identical specification.** See question **C1**.

---

## 1.14 The company's own GSM charts (`GSM- GPM VS SWL-SF.xlsx`)

Transcribed as-is for confirmation. **Note: there is NO U-PANEL table in this file.**

### Two-panel (C-type) cross corner loop — AND — Omega bag cross corner loop
*(both tables in the file are identical)*

| SWL | SF 5:1 fabric | SF 5:1 bottom | Lami | SF 6:1 fabric | SF 6:1 bottom | Lami |
|---|---|---|---|---|---|---|
| 500 | 100 GSM with RF | 100 | 20 | 110 with RF | 110 | 20 |
| 501–750 | 125 with RF | 125 | 25 | 130 with RF | 130 | 25 |
| 751–1000 | 145–150 with RF | 150 | 25 | 160 with RF | 160 | 30 |
| 1000–1250 | 170 with RF | 170 | 30 | 180 with RF | 180 | 30 |
| 1251–1500 | 190 with RF | 190 | 30 | 210 with RF | 210 | 30 |
| 1501–1600 | 200 with RF | 200 | 30 | 225 with RF | 225 | 30–35 |
| 1601–1800 | 225 with RF | 225 | 30–35 | 240 with RF | 240 | 35 |
| 1801–2000 | 240 with RF | 240 | 35 | 150×2 with RF (DOUBLE LAYER) | 150×2 | 25 |

### 4-panel baffle (Q-bag) CROSS CORNER loop

| SWL | SF 5:1 | bottom | Lami | SF 6:1 | bottom | Lami |
|---|---|---|---|---|---|---|
| 500 | 120 with RF | 120 | 20 | 110 with RF | 110 | 20 |
| 501–750 | 135 with RF | 135 | 25 | 130 with RF | 130 | 25 |
| 751–1000 | 150 with RF | 150 | 25 | 160 with RF | 160 | 30 |
| 1000–1250 | 170 with RF | 170 | 30 | 180 with RF | 180 | 30 |
| 1251–1500 | 190 with RF | 190 | 30 | 210 with RF | 210 | 30 |
| 1501–1600 | 200 with RF | 200 | 30 | 225 with RF | 225 | 30–35 |
| 1601–1800 | 225 with RF | 225 | 30–35 | 240 with RF | 240 | 35 |
| 1801–2000 | 240 with RF | 240 | 35 | — | — | — |

### 4-panel baffle (Q-bag) CORNER loop ← *the table an earlier analysis used for U-panel*

| SWL | SF 5:1 | bottom | Lami | SF 6:1 | bottom | Lami |
|---|---|---|---|---|---|---|
| 500 | 110 GSM | NA | 20 | 120 GSM | NA | 20 |
| 501–750 | 125 | NA | 20 | 135 | NA | 25 |
| **751–1000** | **140** | NA | 25 | 150 | NA | 25 |
| **1000–1250** | **155–160** | NA | 25 | 170 | NA | 30 |
| 1251–1500 | 180 | NA | 30 | 200 | NA | 30 |
| 1501–1600 | 190 | NA | 30 | 220 | NA | 30 |
| 1601–1800 | 210 | NA | 30 | 230 | NA | 35 |
| 1801–2000 | 230–240 | NA | 35 | — | — | — |

### Tunnel bag (corner loop)

| SWL | SF 5:1 | Lami | SF 6:1 | Lami |
|---|---|---|---|---|
| 500 | 100 | 20 | 110 | 20 |
| 501–750 | 120 | 20 | 130 | 25 |
| 751–1000 | 125–130 | 25 | 150 | 25 |
| 1000–1250 | 150–155 | 25 | 170 | 30 |
| 1251–1500 | 180 | 30 | 195–200 | 30 |
| 1501–1600 | 190 | 30 | 210–215 | 30 |
| 1601–1800 | 210 | 30 | 225 | 30–35 |
| 1801–2000 | 230–240 | 35 | 140–150 (DOUBLE LAYER) | 25 |

### Belt GPM — TWO PANEL / OMEGA / 4-PANEL BAFFLE (cross corner loop)

| SWL | SF 5:1 width | SF 5:1 GPM | SF 6:1 width | SF 6:1 GPM |
|---|---|---|---|---|
| 500 | 70–75 mm | 35 g | 70–75 mm | 35 g |
| 501–750 | 70–75 mm | 35 g | 75–80 mm | 40 g |
| 751–1000 | 75–80 mm | 40 g | 85–100 mm | 45 g |
| 1000–1250 | 78–100 mm | 45 g | 86–100 mm | 50 g |
| 1251–1500 | 79–100 mm | 50 g | 87–100 mm | 55 g |
| 1501–1600 | 80–100 mm | 50–52 g | 88–100 mm | 55 g |
| 1601–1800 | 81–100 mm | 55 g | 89–100 mm | 60–65 g |
| 1801–2000 | 82–100 mm | 60–65 g | 90–100 mm | 50 g (DOUBLE LAYER) |

### Belt GPM — TUNNEL / BAFFLE / BOX (corner loop) ← *the table used for the 85×85×85 reference*

| SWL | SF 5:1 width | SF 5:1 GPM | SF 6:1 width | SF 6:1 GPM |
|---|---|---|---|---|
| 500 | 40–45 mm | 22–25 g | 40–45 mm | 25–28 g |
| 501–750 | 45–50 mm | 25–28 g | 50 mm | 30–32 g |
| **751–1000** | **50 mm** | **30–35 g** | 50 mm | 40 g |
| 1000–1250 | 50 mm | 40 g | 50 mm | 45 g |
| 1251–1500 | 50 mm | 45–50 g | 50 mm | 50 g |
| 1501–1600 | 50 mm | 50 g | 50 mm | 55 g |
| 1601–1800 | 50 mm | 55 g | 50 mm | 60 g |
| 1801–2000 | 50 mm | 60 g | 50 mm | 40–45 g (DOUBLE LAYER AT FREE HEIGHT) |

> The 85×85×85 reference bag used **50 mm / 35 GPM** — the **top** of the 30–35 band. See question **C5**.

---

## 1.15 What the order actually supplies

Header field blank or "NA", across 395 sheets:

| Field | Absent / NA | % |
|---|---:|---:|
| SWL | 3 | **0.8%** |
| bag weight | 36 | **9.1%** |
| packing | 67 | 17.0% |
| printing | 170 | 43.0% |
| doc pocket | 176 | 44.6% |
| liner | 310 | **78.5%** |

Family distribution across the 395 sheets: **u_panel 174 · circular 113 · baffle 70 · single_loop 14 · four_panel 11 · two_loop 10 · unclassified 133**

---

## 1.16 Sheet structure (all 395 follow this)

```
A1        ANJANI INTERWEAVE [PVT LTD.]
A2        BILL OF MATERIAL
A3/C3     CUSTOMER NAME
A4/C4     ORDER NO.            (also spelt OEDER NO.)
A5/C5     REF NO.
A6/C6     SWL                  e.g. "750 KGS"
A7/C7     SF                   stored as Excel time 5:01 / 6:01
A8/C8     QTY
A9/C9     BAG TYPE             free text, 60 variants
A10/C10   FABRIC COLOR
A11/C11   BAG WT. | REQ. WT. | REW. WT.     <- the target weight
G3        PRINTING  + H3 yes/no, I3 sides, J3 colours, K3 colour
G4        BAG SIZE  + H4 I4 J4 = L W H + K4 "CM" + L4 "EXTERNAL"
G5        BAG SIZE  + ...                        + L5 "INTERNAL"
G6        LOOP      + H6 "4X25" + I6 "LL 60 CM" + J6 "SL 40 CM" + K6 colour + L6 "50 MM/WHITE"
G7        SKIRT TOP | TOP/FS      + spec
G8        BOTTOM/DS               + spec
G9        DOC PKT
G10       LINER
G11       PACKING | CONTAINER DATE

A13:L31   COMPONENT TABLE, 15 fixed rows
          SR NO. | COMPONENT | GSM | LAMI/UL | FABRIC COLOR |
          FABRIC WIDTH (CM) | CUT LENGTH(CM) | CUT PIECE WEIGHT | TOTAL | REMARK
          rows: BODY PANEL, SIDE/BOTTOM PANNEL, TOP PANNEL, FILLING SPOUT,
                D/S, TIE/IRIS ROPE, FS TIE, DS TIE, LOOP, LINER, DDP, DOC,
                STITCHING, PRINTING, LABEL
          closed by GRAND TOTAL

A31-A35   INSTRACTION :- free-text production lines
A36+      TAPE PLANT | LOOM DEPARTMENT | NIDDLE LOOM specs
A42       MIXING     e.g. "PP - 80 % , CC - 8% , UV - 1.5 % , RP - 12.5 %"
A51       PREPARE BY / CHECKED BY / APPROVE BY
```

**Rows are always listed, even when not fitted (weight = 0):**

| Row | Listed | Actually fitted | % fitted |
|---|---:|---:|---:|
| BODY PANEL | 394 | 394 | 100.0% |
| STITCHING | 394 | 394 | 100.0% |
| LABEL | 390 | 377 | 96.7% |
| LOOP | 368 | 363 | 98.6% |
| SIDE PANNEL | 152 | 148 | 97.4% |
| TOP PANNEL | 189 | 131 | 69.3% |
| DOC | 351 | 195 | 55.6% |
| D/S | 187 | 98 | 52.4% |
| PRINTING | 359 | 186 | 51.8% |
| FILLING SPOUT | 184 | 95 | 51.6% |
| DS TIE | 147 | 70 | 47.6% |
| LINER | 176 | 72 | 40.9% |
| DDP | 188 | 54 | 28.7% |

---

## 1.17 Vocabulary found in the data

### Bag type — 60 distinct raw strings (top 45)

```
54  U PANNEL WITH CORNER LOOP              4  U PANNEL BAG
46  U PANNEL BAG WITH CORNER LOOP          4  TUBELAR BAG WITH TOP HEMMING
36  CIRCULAR WITH CROSS CORNER LOOP        4  U+2 PANNEL BAG WITH CORNER LOOP
25  4 PANNEL BAFFLE WITH CORNER LOOP       4  CIRCULAR ROUND BAG WITH FULL RUNNING LOOP
25  CIRCULAR BAG WITH CROSS CORNER LOOP    4  DOUBLE LAYER U-PANNEL BAG
13  4 PANNEL BAFFLE BAG WITH CORNER LOOP   4  4 PANNEL BAG WITH CROSS CORNER LOOP
13  SINGLE LOOP BAG                        4  U+2 WITH DOUBLE LAYER ( STEVE' DOOR)
12  U+2 PANEL WITH CORNER LOOP             4  U+2 (140+25)GSM
11  U PANEL BAG                            3  H BOTTOM BAG
10  CIRCULAR CROSS CORNER                  3  2 LOOP BAG
10  U+2                                    3  CIRCULAR BAG WITH CROSS LOOP
10  CIRCULAR NAG WITH CROSS CORNER LOOP    3  4 PANNEL BAG WITH FLANGE LINER
 9  U-PANNEL BAG                           3  2 LOOP BAG WITH 4 CORNER LOOP
 7  4 PANNEL BAFFLE BAG WITH CROSS CORNER  3  U PANNEL BAG CORNER LOOP
 7  4 PANNEL BAFFLE BAG ( Q BAG )          2  U+2 CORNER LOOP CONDUCTIV
 6  4 PANNEL WITH BAFFLE BAG ( Q BAG )     2  4-PANNEL WITH CORNER LOOP
 5  CIRCULAR                               2  CONTAINER LINER BAG TOP FULL OPEN WITH VELCRO AND BOTTOM SPOUT
 4  CORNER LOOP + BAFFLE BAG               2  CIRCULAR BAG
 4  4-CORNER LOOPBAFFLE BAG                2  4 PANNEL BAFFLE BAG
 4  DOUBLE LOOP TUBELAR BAG                2  CIRCULAR BAG WITH OMEGA DESIGN
                                           2  4 PANNEL WITH LINER BAG
                                           2  U+2 PANNEL BAG
                                           1  4 PANNEL WITH BAFFLE BAG
                                           1  U+2 APNNEL BAG WITH DOUBLE LAYER
                                           1  4 PANNEL BAFFLE WITH CROSS CORNER LOOP
```

Note the typos that still carry meaning: `CIRCULAR NAG`, `4-CORNER LOOPBAFFLE BAG` (no space), `U+2 APNNEL`.

### Component labels — 127 distinct (top 60)

```
394 BODY PANEL        152 SIDE PANNEL       37 SKIRT TIE          19 TOP / FS
394 STITCHING         147 DS TIE            37 DISCHARGE SPOUT    17 STEEVE DORE
390 LABEL             141 TIE/IRIS ROPE     31 F/S                17 TUCKING TIE
368 LOOP              110 BOTTOM PANNEL     31 LOOP PROTECTOR     17 STEEVEDORE
359 PRINTING          109 FS TIE            30 TIE/IRIS           16 EXTRA LOOP
351 DOC                98 BOTTOM PANEL      30 SIDE PANEL         16 TOP BEND
189 TOP PANNEL         79 IRISH TIE         25 TOP                15 FS & DS TIE
188 DDP                72 BAFFLE            25 DUFFLE             14 GLUE
187 D/S                71 TIE               25 FELT               14 F/S , D/S TIE
184 FILLING SPOUT      68 TOP PANEL         24 F/S & D/S TIE      13 FS/ DS TIE
176 LINER              59 D SPOUT           22 BRAIDED ROPE       12 DS/FS TIE
                       52 FS SPOUT          22 TABBING TAPE       10 SUPPORTING TIE
                       51 BAFFLE FABRIC     22 FILLERCORD         10 D/ SPOUT
                       51 SKIRT             21 BELLY BEND          9 DS SPOUT
                       48 TOP SPOUT         20 DS FLAP             8 TIE/DS
                       42 BOTTOM SPOUT      37 FS / DS TIE         8 BELLY BELT
                                                                   8 TOP/SKT
```

**Proposed canonical merges — need confirmation (question E1):**

| Canonical | Raw labels seen |
|---|---|
| DISCHARGE SPOUT | `D/S` · `D SPOUT` · `DS SPOUT` · `DISCHARGE SPOUT` · `BOTTOM SPOUT` · `D/ SPOUT` |
| FILLING SPOUT | `FILLING SPOUT` · `FS SPOUT` · `F/S` · `TOP SPOUT` · `TOP / FS` · `TOP/SKT` · `TOP` |
| SIDE PANEL | `SIDE PANNEL` · `SIDE PANEL` |
| TOP PANEL | `TOP PANNEL` · `TOP PANEL` |
| BOTTOM PANEL | `BOTTOM PANNEL` · `BOTTOM PANEL` |
| BAFFLE | `BAFFLE` · `BAFFLE FABRIC` |
| IRIS TIE | `TIE/IRIS ROPE` · `IRISH TIE` · `TIE/IRIS` · `BRAIDED ROPE` |
| FS TIE / DS TIE | `FS TIE` · `DS TIE` · `TIE` · `FS/DS TIE` · `F/S & D/S TIE` · `FS & DS TIE` · `F/S , D/S TIE` · `DS/FS TIE` · `TIE/DS` · `FS/ DS TIE` · `SUPPORTING TIE` · `TUCKING TIE` · `SKIRT TIE` |
| STEVEDORE LOOP | `STEEVE DORE` · `STEEVEDORE` |
| BELLY BAND | `BELLY BEND` · `BELLY BELT` |
| SKIRT | `SKIRT` · `DUFFLE` |
| FILLER CORD | `FILLERCORD` |
| *(unclassified)* | `FELT` · `GLUE` · `TABBING TAPE` · `TOP BEND` · `DS FLAP` · `LOOP PROTECTOR` · `EXTRA LOOP` |

### Production instruction lines — 127 distinct (top 45)

```
16  TOP AND BOTTOM ROUND DOUBLE CHAIN STITCHING WITH WHITE YARN
14  ALL SEAM DOUBLE DUST PROOF
12  U+2 PANEL BAG WITH J FOLD BOX STITCHING AND TOP OUT FOLD
12  LOOP TO BE PLACED OUTSIDE BLUE COLOR WITH POLYSTER YARN 10000 DNR
12  STITCHING DOUBLE CHAIN WITH WHITE YARN 3% UV TREATED MINIMUM YARN DNR 3200
12  PACKING SHOULD BE 50 PCS PER BALE WITH PALLET FUMIGATED PALLET TO USED
 9  TOP SPOUT TIE TAPE OUTER FIXED AT 25 CM FROM TOP
 9  U PANNEL BAG WITH CORNER LOOP
 8  TOP AND BOTTOM ROUND SINGLE DOUBLE FOLD STITCHING WHITE YARN
 8  COMPANY LABEL AND DOCUMENT POUCH WITH FRONT SIDE OPEN FABRIC DOC SAME COLORE AS BODY FABRIC
 8  4 PANNEL BAG BAFFLE WITH CORNER LOOP
 8  STITCHING OVER LOCK AND CHAIN STITCHING BLUE AND WHITE YARN
 7  BOTTOM J FOLD AND TOP OUT FOLD STITCHING 3200 DNR WHITE YARN OVERLOCK + CHAIN
 7  BELT 50 CM ATTECHED BY 6 PASS JUKKI MINIMUM 2000 KGF STRENGTH
 7  TOP PERIMETER DOUBLE DUST PROOF AND REST ALL SEAM SINGLE DUST PROOF
 7  BAG WT +/-2 %
 6  ALL FOLD J- FOLD IN BODY
 6  TOP FOLD OUT SIDE
 6  SAFTY IN WHITE 2200 DNR AND OVER LOCK WITH 3600 DNR BLUE
 6  STITCHING HR+DR WITH BLUE AND WHITE YARN
 6  CIRCULAR BAG WITH TOP OUT FOLD AND BOTTOM J-FOLD STITCHING PP BLUE YARN HR+DR
 6  4 BAFFLE WITH 80+20 GSM ONE SIDE LAMINATED 10 HOLES AND STITCHING FROM BOTOOM AND TOP 10 CM
 6  CIRCULAR BAG WITH TOP AND BOTTOM J-FOLD STITCHING TOP AND TOP ROUND WITHOUT DDP AND BOTTOM AND ROUND DDP
 6  BOTTOM OUT FOLD AND TOP OUT FOLD
 6  U PANNEL BAG WITH CORNOR LOOP BLUE AND WHITE STRIPES
 6  STITCHING OVERLOCK+CHAIN STITCHING BLUE YARN
 6  TOP SPOUT DOUBLE CHAIN STITCHING
 6  PACKING 200 PCS PER PALLET 48 PALLET 48X200 = 9600 PCS IN CONTAINER
 5  LOOP OUT SIDE STITCHING WHITE COLOR
 5  QUANTITY OF BUNDLE 60 BAG'S OF EACH.
 5  ALL SEAM OUT SIDE FOLD BUTTERFLY
 5  MAKE SURE THE BAG IN SIDE AND OUT SIDE CONTAMINATION FREE
 4  CIRCULAR BAG WITH TOP AND BOTTOM J-FOLD STITCHING
 4  JUKKI 6 PASS STITCHING WITH WHITE BLUE
 4  COMPANY LABEL AND DOCUMENT POUCH WITH BACK SIDE FLAP RHS OPEN
 4  LINER 200X360 CM 55 MICRON BOTH SIDE OPEN LOOSELY LINER FULL GUESTED
 4  4 PANNEL BAFFLE BAG WITH TOP AND BOTTOM OT-FOLD STITCHING PP BLUE YARN HR+DR
 4  COMPANY LABEL AND DOCUMENT POUCH WITH RHS OPEN
 4  U+2 PANNEL BAG WITH DOUBLE LAYER BAG
 4  BOX J-FOLD TOP OUT FOLD STITCHING BLUE AND WHITE YARN
 4  BOTTOM J-FOLD AND TOP OUT FOLD
 4  BOX J FOLD AND TOP OUT FOLD STITCHING
 4  OPEN TOP AND FLAT BOTTOM WITH TOP HEMMING
 4  HR AND DR STITCHING WITH BLUE AND WHITE YARN
```

### Raw-material mixing recipes found

```
PP - 80 %   , CC - 8%  , UV - 1.5 % , RP - 12.5 %
PP - 80.5 % , CC - 8%  , UV - 1.5 % , RP - 10 %
PP - 88.5 % , CC - 10% , UV - 1.5 %              (from the 85x85x85 reference sheet)
```

---

## 1.18 Rules from published FIBC practice (external sources)

Cross-checked so the questions are asked in the industry's own terms. **Confirm these match Anjani practice.**

| Topic | Published practice |
|---|---|
| **Construction families** | U-panel = one U-piece forms bottom + two sides, plus two panels. 4-panel = four pieces sewn to a square. Circular/tubular = woven as a tube, seams only top and bottom. |
| **Shape retention** | 4-panel > U-panel > circular. Cost runs the other way. |
| **Baffle / Q-bag** | "Baffled", "formstable" and "Q-bag" all name the same thing — internal corner panels that stop the bag bulging. |
| **Safety factor** | 5:1 = single-trip. 6:1 = multi-trip and UN-certified. Not a free choice — dictated by the customer's use case. |
| **Governing standard** | ISO 21898 (FIBC construction and testing). Also AS 3668. |
| **Type A** | Plain woven PP, no static protection. Non-flammable contents only. |
| **Type B** | Low breakdown voltage, prevents propagating brush discharge. Dry flammable powders only, no flammable solvents or gases present. |
| **Type C** | Conductive threads interwoven. **Must be electrically grounded** during fill and discharge. |
| **Type D** | Static-dissipative fabric (e.g. CROHMIQ). No grounding required. |
| **Manufacturing sequence** | Tape extrusion (virgin PP + CaCO₃ + UV masterbatch, drawn to denier and tenacity) → weaving on flat or circular looms → separate needle-loom production of webbing → cutting → printing → stitching → finishing. |
| **Denier** | Grams per 9,000 m of yarn. So `3200 DNR` is a thickness spec, not a weight. |
| **Filler cord** | PP rope or braided cord sewn into a seam to stop fine dust escaping — makes the bag sift-proof. |
| **Hemming** | Fold-and-sew (or glue) that stops cut fabric fraying and adds seam strength. |
| **Liner types** | Form-fit (fits the interior exactly, for contamination-critical), gusseted (pleated sides, larger volumes), lay-flat (unfolds during filling, suits automated lines). |
| **Document pouch** | PE or PP pouch for shipping/identifying documents. Also called pocket or envelope. |

**Sources:**
- https://blog.nationalbulkbag.com/fibc-bulk-bag-construction/types-of-jumbo-bag-construction-upanel-circular-4panel
- https://www.southernpackaginglp.com/blog/baffled-formstable-q-bag-why-you-should-be-using-this-type-of-fibc
- https://codefine.com/blog/products-and-materials/fibc-safety-factors-what-they-mean-and-why-they-matter/
- https://smartpackgroup.com/iso-21898-as-3668-bulk-bag-safety/
- https://www.nationalbulkbag.com/types-of-fibc-bulk-bags-a-b-c-d-explained/
- https://www.bulkcorp-int.com/blog/fibc/the-steps-involved-in-fibc-bags-manufacturing-process/
- https://codefine.com/blog/manufacturing-process-of-fibc-bags/
- https://cleanitup.com/understanding-terms-used-bulk-bags-fibc/
- https://flexsack.com/fibc-liner-selection-guide/

---
---

# PART 2 — QUESTIONS FOR THE ENGINEER

**44 questions. 15 marked [BLOCKING].**

The blocking ones — **A1, A2, B1, B2, B6, C1, C2, C3, C6, D1, E1, E3, G1, G2, G3** — are worth a single sitting, in that order. They are not independent: B1 and B2 together fix the geometry, C1–C6 fix material selection, G1–G3 define the solver.

Where the answer is "it depends" — **that is the most valuable answer in the document.** It names a field we are not currently capturing, and every such field is one the model will otherwise have to guess.

---

## A · Classification and defaults
*Because misclassifying the construction poisons every number downstream*

### A1. [BLOCKING]
**When the customer says only "open top, flat bottom" and gives no construction — you default to U+2. Is that always the default, or does it change with bag size, SWL, product density, or whether it is an export order?**

> *Evidence:* Our example query has no construction stated and was built as U-Panel corner loop. Across the corpus the family split is **u_panel 174 · circular 113 · baffle 70 · 4-panel 11** — so circular is common enough that "always U+2" needs confirming.

### A2. [BLOCKING]
**What makes you choose *corner loop* versus *cross-corner loop*? Is it the construction, the SWL, the customer, or something about how they lift?**

> *Evidence:* Circular bags are cross-corner on 71 of 113 sheets; U-panel is corner loop on essentially all. But `4 PANNEL BAFFLE` appears with both. The choice drives a completely different GSM table and belt table.

### A3.
**Are these all the same construction, or do any differ? `U PANNEL` · `U-PANNEL` · `U PANEL BAG` · `U+2` · `U+2 PANEL` · `U+2 PANNEL`**

> *Evidence:* Five spellings, 174 sheets. Assuming they are one family; if `U+2` ever means something different from `U PANNEL`, the whole u_panel group is contaminated.

### A4.
**Is `DOUBLE LAYER U-PANNEL BAG` a separate construction, or U-panel with a modifier? Same question for `U+2 WITH DOUBLE LAYER (STEVE' DOOR)`.**

> *Evidence:* 4 sheets each. Body-panel implied quantity is 2 on some U-panel sheets, which is what a double layer would look like — but I cannot tell it apart from an extraction error.

### A5.
**Which of these do we need to support, and which are one-offs we can leave out of v1? `H BOTTOM BAG` · `OMEGA` · `TUNNEL` · `TUBELAR WITH TOP HEMMING` · `CONTAINER LINER BAG` · `2 LOOP` · `SINGLE LOOP` · `CIRCULAR ROUND WITH FULL RUNNING LOOP`**

> *Evidence:* Between 2 and 14 sheets each — enough to name, not enough to learn a rule from.

### A6.
**Does *Q-bag* always mean 4-panel baffle, or can a Q-bag be built on a circular body?**

> *Evidence:* `4 PANNEL BAFFLE BAG ( Q BAG )` appears 7 times, `4 PANNEL WITH BAFFLE BAG ( Q BAG )` 6 times. Industry usage treats Q-bag as any formstable baffled FIBC, which is broader.

---

## B · Cut sizes and seam allowances
*Because one sheet disagrees with the other 138 and it happens to be the example we are building against*

### B1. [BLOCKING]
**U-panel body cut length: is the standard `2H + L + 10` or `2H + L + 8`? What makes it change?**

> *Evidence:* +10 on **138 of 174** sheets (79%), +8 on 12 (7%). But the 85×85×85 sheet you gave me as the reference uses **+8** (cut 263 = 170 + 85 + 8). By customer: EXPORT ENQUIRY 29/31 use +10; VIJAYNAGAR 3/4 use +8; DOMESTIC uses +3, +6 and +8.

### B2. [BLOCKING]
**Are all cut sizes computed from the *external* dimensions, or does any component work off internal?**

> *Evidence:* Every rule I fitted works off external and lands on a clean +8/+10. Your sheets state both sizes (external usually internal + 4 to 5 cm). If any component is actually cut off internal, that rule is wrong by 4–5 cm and I would not detect it.

### B3.
**Confirm the fixed U-panel set: body width = W + 8, side panel = (L + 8) × (H + 8), quantity 2. Is the +8 four centimetres of seam on each edge?**

> *Evidence:* 94%, 94% and 98% agreement respectively. The `3_Corrected_UPanel` sheet in your variance analysis says "4 cm seam each long edge", which fits.

### B4.
**Circular body: is the flat woven width exactly `W + L` with no seam allowance because it comes off the loom as a tube? And is the body always counted as 2 walls?**

> *Evidence:* Mode of (width − W) is 90 on square 90×90 bags, i.e. width = W + L. Body implied quantity is 2 on 39% of all sheets, which is close to the circular share (113/395).

### B5.
**Why do circular top/bottom panels use +10 while baffle top/bottom use +8?**

> *Evidence:* Circular top/bottom: +10 on 86% of 94. Baffle top/bottom: +8 on 61% of 70. Consistent enough to be deliberate, but I do not know the reason and cannot generalise it to a new family without one.

### B6. [BLOCKING]
**Do you round the computed fabric width *up to an available loom width*, or does the loom get set to whatever the calculation says?**

> *Evidence:* On the 85×85×85 sheet, body and side are both 93 cm — one loom setting serves both. That looks deliberate. But if loom width is a hard constraint, the whole geometry needs a snap-to-available-width step; if not, it must not have one. **What are the actual available widths?**

### B7.
**Filling and discharge spouts — what are the width and cut formulas? Is the stated size (e.g. `40×50 CM`) a diameter or a flat width, and which of the two numbers is the height?**

> *Evidence:* Observed: FS `40×50` → 55 × 137.6 cut; DS `35×50` with iris → 85 × 122; DS `40×50` iris → 85 × 137.6. I can see the pattern but cannot pin the formula, and the same stated size gives different widths on different sheets.

### B8.
**How much extra fabric and tie length does each closure add — *open/tied*, *iris*, *petal*, *pyjama*?**

> *Evidence:* Iris rope cut lengths observed: 165, 195, 175 cm on otherwise similar bags. Tie rows run 125–195 cm at 6–7 g/m.

---

## C · GSM selection — the biggest gap
*Because the same bag was built at 125 and at 210*

### C1. [BLOCKING]
**Two orders, same construction, same 90×90×110 cm, same SWL 1000 kg, same 5:1 — one built at 125 GSM, one at 210. What is the difference between those two orders?**

> *Evidence:* This is the question the whole project turns on. 24 of 108 identical-spec groups disagree on body GSM. If the answer is "the customer's product" or "export versus domestic" or "how many trips they reuse it", that field has to be captured in the enquiry and fed to the model.

### C2. [BLOCKING]
**Do you work *forward* from SWL and safety factor to a GSM, or *backward* from the customer's required bag weight to whatever GSM lands on it?**

> *Evidence:* The data says backward: the component total is within 2% of the stated bag weight on 78% of 350 sheets. Inverting the weight formula predicts the chosen GSM with a median error of 0.00%, against 3.33% for the load-chart cell. If that is really how you work, the software should work that way too.

### C3. [BLOCKING]
**Your `GSM- GPM VS SWL-SF.xlsx` has tables for two-panel, omega, 4-panel baffle (both loop types) and tunnel — but *no U-panel table*. Which table do you read for a U+2 bag?**

> *Evidence:* U-panel is 44% of the corpus and has no chart. An earlier analysis assumed the 4-panel corner-loop column (140 GSM at 751–1000 kg, 5:1), which would make the 85×85×85 bag's 150 GSM a +7% margin. Please confirm or correct.

### C4.
**SWL of exactly 1000 kg falls in both the `751–1000` and `1000–1250` rows. Which one wins?**

> *Evidence:* 1000 kg is the single most common SWL in the corpus, so this boundary is hit constantly. The two rows differ by 15–20 GSM.

### C5.
**Where the chart gives a range — `145–150 GSM`, `155–160`, `230–240` — what makes you take the top rather than the bottom?**

> *Evidence:* On the 85×85×85 bag the belt chart said 30–35 GPM and you took 35, the top of the band. Is that habitual, or was there a reason on that order?

### C6. [BLOCKING]
**If the customer *states a GSM* and it is below the chart minimum for their SWL and safety factor — what do you do?**

> *Evidence:* This decides whether the software may ever go below the chart. It is the safety question in the whole system.

### C7.
**The remark column writes lamination as `70+20 LAMINATED` — base fabric plus coating. Is the GSM column always the *total* (90), never the base?**

> *Evidence:* `70+20 LAMINATED` appears on 184 rows, and the GSM column reads 90 alongside it. Confirming, because if it is ever the base figure the weight is out by 20–30%.

### C8.
**What does `175+30 UNLAMINATED` mean? And is `15+90+15` both-side lamination?**

> *Evidence:* 12 rows say a lamination figure and then "UNLAMINATED". 9 rows use the three-part form. Both look deliberate rather than typed wrong.

### C9.
**Which components take a different GSM from the body as a matter of course, and what governs each — top panel, spouts, baffle, bottom?**

> *Evidence:* Observed: top panel 80–120 laminated, spouts almost always 90 (`70+20`), baffle 130 both-side laminated, circular bottom heavier than body per the chart. Looks like a fixed policy rather than a per-order choice.

---

## D · Lifting loops and webbing
*Because loop length is a third of the bag's weight and is not derivable from the size*

### D1. [BLOCKING]
**Confirm loop cut = `2 × free height + LL + SL`, quantity 4. And are LL and SL given by the customer, or chosen by you?**

> *Evidence:* The formula reproduces exactly on 197 of 226 sheets. Observed ranges are wide: free height 22–122 cm, LL 30–140, SL 30–96 — so if the customer does not state them, something else decides.

### D2.
**A 50 mm belt appears at 28, 30, 32, 35, 40, 42, 45 and 50 g/m. What picks the gramage once the width is fixed?**

> *Evidence:* Eight gramages at one width, 184 sheets. The belt chart bands by SWL and safety factor but does not explain this much spread.

### D3.
**Does the belt gramage in the BOM ever differ from the needle-loom GPM spec on the same sheet?**

> *Evidence:* On the 85×85×85 sheet, input cell "Loop Belt GPM" reads 28 while the component table and the loom requirement both use 35. One of those is stale — I would like to know which is authoritative.

### D4.
**When do you fit a *loop protector*, *extra loop*, *stevedore loop*, or *full running loop*?**

> *Evidence:* Loop protector on 31 sheets, stevedore 34, extra loop 16, full loop 4. Too rare to infer a rule, common enough to need one.

### D5.
**What does the belt strength requirement depend on, and where is it specified?**

> *Evidence:* One needle-loom block reads `STRENGHT 1680 KGF`; an instruction line reads `BELT 50 CM ATTECHED BY 6 PASS JUKKI MINIMUM 2000 KGF STRENGTH`. Two different numbers, unclear which governs.

---

## E · Which components go in
*Because half the fifteen rows are conditional and the sheet does not say why*

### E1. [BLOCKING]
**Please confirm the canonical component list and tell me which of these 127 raw labels are genuinely the same thing.**

> *Evidence:* Candidates to merge — **discharge spout:** `D/S · D SPOUT · DS SPOUT · DISCHARGE SPOUT · BOTTOM SPOUT · D/ SPOUT`. **Filling spout:** `FILLING SPOUT · FS SPOUT · F/S · TOP SPOUT · TOP / FS · TOP/SKT`. **Ties:** `FS TIE · DS TIE · TIE · FS/DS TIE · F/S & D/S TIE · TIE/DS · SUPPORTING TIE · TUCKING TIE · SKIRT TIE`. **Iris:** `TIE/IRIS ROPE · IRISH TIE · TIE/IRIS · BRAIDED ROPE`. *(Full list in §1.17.)*

### E2.
**What are *FELT*, *GLUE*, *TABBING TAPE*, *BELLY BEND*, *TOP BEND*, *DS FLAP* and *DS PATCH*, and when does each get fitted?**

> *Evidence:* Felt 25 sheets, glue 14, tabbing 22, belly bend 21, top bend 16, DS flap 20. None appear in any rule table we have.

### E3. [BLOCKING]
**DDP — what unit is the cut length in, and how many pieces per bag?**

> *Evidence:* Reconciling weight against 4.5 g/m gives an implied quantity of **100** on 48 of 52 sheets. Either the length is in metres while the column says cm, or the row records 100 bags at once. Until this is settled every DDP weight in the training data is wrong by 100×.

### E4.
**What is the difference between *DDP*, *filler cord*, *triple dust proof* and "all seam double dust proof"? Are they alternatives or do they stack?**

> *Evidence:* 14 instruction lines say `ALL SEAM DOUBLE DUST PROOF`; 7 say `TOP PERIMETER DOUBLE DUST PROOF AND REST ALL SEAM SINGLE`. The component rows do not obviously change with them.

### E5.
**When the customer does not mention a liner, doc pocket or printing — is the answer always no, or do some customers get them by default?**

> *Evidence:* Header field blank or "NA": liner 78.5%, doc pocket 44.6%, printing 43.0%. But of the sheets that *list* a doc pocket row, 55.6% actually fit one — so it is not a simple default.

### E6.
**Top construction — what decides between *open top*, *top panel*, *skirt/duffle*, *top flap* and *spout* when the customer has not said?**

> *Evidence:* Top panel appears on 189 sheets, skirt on 51, duffle on 25. Our example query said "open top" explicitly, so it is fine — but most of the corpus is not that clear.

### E7.
**Liner: what governs micron, whether it is loose / tabbed / glued / hemmed, and its cut size?**

> *Evidence:* Observed 50–100 micron; instruction lines mention `LOOSELY INSERTED BOTTOM SEALED`, `FULL GUESTED`, tabbing and glueing. Liner cut sizes such as `200×360 CM` do not follow obviously from the bag size.

---

## F · Stitching, yarn and production instructions
*Because these lines are part of the BOM and the model will have to write them*

### F1.
**Is the sewing-yarn weight a formula, or do you pick a round number from experience?**

> *Evidence:* Yarn weight divided by bag height has a median of 0.467 g/cm — close to the 0.45 rule of thumb — but the tenth-to-ninetieth percentile spans 0.33 to 0.72. The values used are round: 55 g on 45 sheets, 60 g on 62, 65 g on 35. That looks chosen, not calculated.

### F2.
**What decides the stitch specification — *HR+DR*, *overlock + chain*, *double chain*, *single fold*, *butterfly*?**

> *Evidence:* All appear as instruction lines, up to 16 times each. Is it construction, customer, or product?

### F3.
**Yarn denier appears as 2200, 3000, 3200 and 3600, sometimes two in one bag (`SAFTY IN WHITE 2200 DNR AND OVER LOCK WITH 3600 DNR BLUE`). What selects them, and what does the colour convention mean?**

> *Evidence:* 6 sheets use that exact two-yarn line. Blue and white recur throughout — I assume white is safety stitch and blue overlock, but that is a guess.

### F4.
**Fold type — *J-fold*, *out-fold*, *box J-fold*, *top hemming* — is this determined by construction, or is it a customer preference?**

> *Evidence:* `U+2 PANEL BAG WITH J FOLD BOX STITCHING AND TOP OUT FOLD` on 12 sheets; `CIRCULAR BAG WITH TOP AND BOTTOM J-FOLD` on 6. It looks construction-linked but not exclusively.

### F5.
**Should the generated BOM produce the *INSTRACTION* lines, the *TAPE PLANT / LOOM / NIDDLE LOOM* specs and the *MIXING* recipe — or does the plant fill those in later?**

> *Evidence:* They are present on most sheets but not all, and the mixing recipe is legible on only a handful. If they are part of the deliverable, we need the rules; if they are added downstream, we can leave them out and the scope shrinks usefully.

### F6.
**What drives the raw-material blend? Observed `PP 88.5 / CC 10 / UV 1.5` and `PP 80 / CC 8 / UV 1.5 / RP 12.5`.**

> *Evidence:* Is RP (recycled) allowed only for domestic orders? Does UV always sit at 1.5%? Does CaCO₃ change with GSM?

---

## G · Target weight, tolerance, and impossible orders
*The behaviour you said you want the system to have*

### G1. [BLOCKING]
**Is ±2% the standard tolerance on bag weight? Does it change by customer or by whether the order is export?**

> *Evidence:* `BAG WT +/-2 %` appears verbatim on 7 sheets, and 78% of all 350 measurable sheets land inside 2%. If ±2% is the rule, it becomes the solver's stopping condition.

### G2. [BLOCKING]
**When the customer's required weight cannot be met safely — as in this very enquiry, 720 g against a 140 GSM floor that forces 836 g — what do you actually do?**

> *Evidence:* Options I can see: quote the safe weight and tell them; ask them to reduce SWL; ask them to accept 6:1 → 5:1; change construction; refuse. The 85×85×85 order ended up written as 0.88 kg. What was said to the customer?

### G3. [BLOCKING]
**When the total comes out over or under target, which knob do you turn first — body GSM, loop gramage, lamination, spout size, yarn?**

> *Evidence:* This is literally the algorithm. If GSM is the first lever and loop gramage the second, the solver adjusts them in that order and will reproduce your reasoning rather than inventing its own.

### G4.
**Is the "BAG WT." on the sheet the customer's requirement, or the weight you quoted back to them?**

> *Evidence:* The header uses three different labels — `BAG WT.`, `REQ. WT.`, `REW. WT.`. If they mean different things, the training data must keep them apart.

### G5.
**Roughly what share of enquiries arrive with something wrong or missing, and what are the three mistakes you correct most often?**

> *Evidence:* You have said the engineer spots impossible specs by experience. Naming the top three lets us build them as explicit checks and test the system against them.

### G6.
**If SWL or safety factor is missing entirely, what do you assume?**

> *Evidence:* Only 3 of 395 sheets lack SWL, so it is rare here — but the system will meet it, and guessing silently is the failure mode we most want to avoid.

---

## H · Practical, for building the system

### H1.
**Which sheets should the model learn from, and which are drafts, samples or superseded?**

> *Evidence:* `DOMESTIC ENQUIRY.xlsx` holds 81 sheets and appears three times in different folders; `EXPORT ENQUIRY.xlsx` exists in three copies. Training on duplicates teaches the model those bags are three times more likely than they are.

### H2.
**Which named customers are the "house style" reference — the orders that best represent how a bag should be built?**

> *Evidence:* Useful for weighting the training set and for choosing the twenty regression cases the system must never get wrong.

### H3.
**Are there any recent BOMs the engineer would now build differently? Any rule that changed in the last year or two?**

> *Evidence:* The corpus spans 2023 to 2026. If a standard changed, old sheets are actively misleading and should be down-weighted or excluded.

### H4.
**How does the enquiry actually arrive — WhatsApp, email, a scanned technical data sheet, a phone call written up afterwards? Could we keep the raw text of the next twenty as they come in?**

> *Evidence:* The corpus holds the *outputs*, but the model's input at run time is the raw enquiry, and we have almost no real examples of those. Twenty genuine ones would be worth more than a thousand synthesised.

### H5.
**When the system produces a BOM, what would the engineer want to see in order to trust it in ten seconds?**

> *Evidence:* Which lines differ from the nearest historical bag? Which numbers came from a chart, which from judgement? Getting this right decides whether it gets used.

### H6.
**Is `FIBC PRODUCTION DEC-2025.xlsx` recoverable? It is an `.xls` file with an `.xlsx` name and nothing can open it.**

> *Evidence:* Also, the file given as `90X90X90 CM.xlsx` contains an 85×85×85 bag. If filenames are unreliable, we must never use them to label training data.

---

## Two additional asks, beyond answering the questions

1. **Walk one enquiry out loud.** Take a recent order and have the engineer narrate every decision from reading the customer's message to signing the sheet — including the ones he makes without noticing. That transcript is worth more than any single answer above.

2. **Keep the next twenty raw enquiries.** Screenshots, forwarded emails, WhatsApp text, scans — untouched, exactly as received. We have 395 finished BOMs and almost no examples of what the model will actually be given as input.

---

## Worked example — the enquiry under discussion

```
Bag size : 85x85x85
Bag type : open top flat bottom
GSM      : 150
SWL      : 1000 kg
SF       : 5:1
Weight   : 720 g
```

Applying the rules in Part 1 (U-panel, corner loop, 4 loops at 35 GPM × 150 cm, yarn 40 g, label 2 g):

| Body GSM | Body (g) | Sides ×2 (g) | Loops (g) | Yarn + label (g) | **Total (g)** | Status |
|---:|---:|---:|---:|---:|---:|---|
| 110 | 269.05 | 190.28 | 210.00 | 42.00 | **711.33** | below load-chart floor |
| 120 | 293.51 | 207.58 | 210.00 | 42.00 | **753.08** | below load-chart floor |
| 140 | 342.43 | 242.17 | 210.00 | 42.00 | **836.60** | lightest legal build (chart minimum) |
| **150** | **366.89** | **259.47** | **210.00** | **42.00** | **878.36** | **matches the production sheet exactly** |

Geometry used: body `93 × 263`, side `93 × 93 × 2`, loop cut `2(25) + 65 + 35 = 150`.

**The query is self-contradictory.** 720 g and 150 GSM cannot both hold. 720 g needs roughly 112 GSM, which is below the 140 GSM floor for a corner-loop bag at SWL 1000 / SF 5:1. The production sheet resolved it by building at 150 GSM and recording "Bag Weight Required = 0.88 kg".

This is the case questions **G2** and **G3** are about.

---

*End of document.*
