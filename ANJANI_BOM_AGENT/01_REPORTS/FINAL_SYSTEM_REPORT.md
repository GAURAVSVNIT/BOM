# Anjani FIBC BOM Agent — Final System Report

**Prepared:** 12 August 2026
**Basis:** The engineer's answers to all 44 questions, tested against **395 BOM sheets** parsed from `All_Things`. Domain material cross-read from `fibc/01`–`09`, the National Bulk Bag *Bulk Density List* (28 pp), *Buyer's Guide to UN Certified Bulk Bags*, and *A Buyer's Guide to Purchasing Bulk Bags*.
**Scope:** Costing excluded per instruction. Tape-plant / loom / needle-loom / INSTRACTION blocks included.

> **Four rules are marked DISPUTED. They must not be coded until confirmed — see §2.**

---

## Contents

1. [What the answers changed](#1--what-the-answers-changed)
2. [Four rules that fail against the data](#2--four-rules-that-fail-against-the-data)
3. [The confirmed rule book](#3--the-confirmed-rule-book)
4. [The architecture, final](#4--the-architecture-final)
5. [Data preparation and fine-tuning](#5--data-preparation-and-fine-tuning)
6. [What is still needed](#6--what-is-still-needed)
7. [Build order](#7--build-order)

---
---

# 1 · What the answers changed

Eleven decisions that were open are now closed. Two of them **delete work**.

| Q | What we assumed | What he said | Effect |
|---|---|---|---|
| **B6** | Snap fabric width up to an available loom width | "The loom gets set to whatever the calculation says" | ✅ **Delete a whole stage.** No loom table needed. |
| **C6** | Chart GSM is a hard floor; never go below | "Nothing, we proceed as per customer's requirement" | ⚠️ The floor becomes a **warning**, not a reject, when the customer states a GSM. |
| **G3** | Adjust body GSM first to hit target weight | "First change is loop gramage and loop cut length. Next in line is body GSM" | ⚠️ **Solver knob order reverses.** Loop before fabric. |
| **C1** | Unknown driver behind the 68% GSM spread | "The product for which the bag will finally be used — clearly mentioned by the customer" | ⚠️ `product_contents` becomes a **required OrderSpec field**. |
| **C2** | Always solve backward from target weight | "If weight specified → work accordingly. If not → forward from SWL/SF" | ⚠️ **Two modes**, chosen by whether a target exists. |
| **E3** | DDP = dust discharge port, a small tube | "DDP stands for **double dust proof** — seam metres × 2 × 4.5 g/m" | ✅ Resolves the qty-100 anomaly. It was cm read as metres. |
| **G2, G5** | System decides, or reports infeasible | "We clarify with the client… I'd like the agent to identify what's missing and raise queries" | ⚠️ **A clarification list becomes a first-class output**, alongside the BOM. |
| **G6** | Guess or refuse when SWL is missing | "Check if he mentioned material density and volume, then compute SWL" | ⚠️ Adds a **bulk-density lookup path**. |
| **A5** | Four families in v1, rest later | "We need to support all and cannot leave anything out" | ⚠️ **Twelve families** from day one. |
| **B7, B8** | Spout formulas unknown | Complete formulas given | ✅ **94.5% / 93.4% verified** against the corpus. |
| **A1, A2** | Family and loop type inferred from context | "U+2 default. Circular only if belt ≥70 mm. Cross-corner if 70–100 mm" | ✅ Classification becomes a **deterministic rule**, not a model judgement. |

### The most important single answer

**C1.** The 68% GSM spread on identical specifications is explained by **the product the bag will carry**, and the customer states it. That was the one thing nothing in the sheets could explain. It is now a field — and it means the extractor must capture free-text product names, and retrieval must weight them.

---
---

# 2 · Four rules that fail against the data

Every stated rule was tested on all 395 sheets. These four do not reproduce. **His answer is the rule going forward — but the disagreement is large enough that writing code on it without one more sentence would be reckless.**

## ① B1 — the +8 / +10 body cut

He says: *"2H+L+8 is the standard, but we use 2H+L+10 when the body fabric GSM is less than 120 and the bag height is above 100 cm."*

Split exactly as the rule describes, U-panel, n=174:

| Body GSM | Height | n | used +10 | used +8 | Rule predicts |
|---|---|---:|---:|---:|---|
| < 120 | > 100 cm | **1** | 100% | 0% | +10 ✓ (but n=1) |
| < 120 | ≤ 100 cm | **0** | — | — | +8 — no data |
| ≥ 120 | > 100 cm | **115** | **72.2%** | 10.4% | ❌ +8 |
| ≥ 120 | ≤ 100 cm | **58** | **93.1%** | 0% | ❌ +8 |

The conditional cell contains a **single sheet**. In the two cells where the rule predicts +8, the plant used +10 on **72% and 93%** of bags. Even the 85×85×85 reference sheet he supplied — GSM 150, height 85, squarely in the "+8" cell — is one of only four sheets in 58 that uses +8.

> **ASK:** *"Your 395 historical U-panel sheets use +10 on 79% of bags including almost every one at GSM ≥ 120. Is +8 a new standard you have moved to, or should the system use +10 and treat +8 as the exception?"*

Every U-panel bag's body weight depends on the answer — about 3 g at 150 GSM, inside ±2% tolerance but it shifts every bag the same way.

## ② F1 — yarn weight per family

| Family | n | He says | Median | Most common values | Verdict |
|---|---:|---:|---:|---|---|
| circular | 113 | 60 g | 60 g | 60 (×36), 55 (×27), 65 (×15) | ✅ **confirmed exactly** |
| u_panel | 174 | 45 g | 50 g | 60 (×25), 45 (×25), 55 (×16), 42 (×15) | ⚠️ plausible, wide spread |
| baffle | 70 | 72 g | **100 g** | 90 (×20), 110 (×16), 100 (×13) | ❌ **off by ~40%** |
| single_loop | 14 | 35 g | **25 g** | 22 (×6), 25 (×5) | ❌ **off by ~40%** |

Baffle bags carry four extra internal panels and far more stitching, so 100 g is physically more plausible than 72 g.

> **ASK:** re-confirm baffle and single-loop specifically.

## ③ D5 — belt strength, 1 gram carries 35 kg

Applied as `GPM × 35 × 4 loops ≥ SWL × SF`, satisfied on only **39.3%** of 321 testable sheets. Shortfalls include ordinary production bags — SWL 1000 at 5:1 with a 30 g/m belt gives 4,200 kg against 5,000 needed.

**Likely resolution:** each corner loop has **two load-bearing legs**, so capacity is `GPM × 35 × 4 × 2`. That makes the same bag 8,400 kg against 5,000 — and it matches published guidance that all four loops carry in tandem.

> **ASK:** *"Does each corner loop count as two load-bearing legs for the 35 kg/gram rule?"* One sentence turns this into an excellent hard validator.

## ④ B8 — iris tie length

`D × 3.14 + 38` is **exact** on the cases verifiable by hand — a 40 cm spout gives 165 cm, a 50 cm spout gives 195 cm, both matching production sheets — and the 38 cm decomposes exactly as he describes (two ties, 10 cm outside each side, two knots of 9 cm). But swept across the corpus it lands within 2 cm on only **33%** of 116 sheets.

Most likely cause is our own parsing: the diameter read from the header is not always the spout the iris tie belongs to, and petal closures are mixed in. Probably a measurement artefact rather than a wrong rule — **re-test after the extractor is rebuilt, before trusting the formula.**

---
---

# 3 · The confirmed rule book

Everything below is now locked.

## 3.1 Classification — fully deterministic

```
FAMILY
  customer names a construction        → use it
  belt width >= 70 mm stated           → circular
  otherwise                            → u_panel (U+2)          // house default, A1
  ambiguous / high value               → raise a clarification, do not guess

LOOP TYPE
  stated explicitly                    → use it
  belt width 70–100 mm                 → cross_corner
  otherwise                            → corner                  // A2

ALIASES  U PANNEL = U-PANNEL = U PANEL BAG = U+2 = U+2 PANEL = U+2 PANNEL   // A3
         Q BAG = 4-panel baffle, always                                     // A6
         DOUBLE LAYER U-PANEL = 2 body fabrics + 2 side fabrics per side    // A4
         STEVEDORE ("steve door") = an attachment, not a family             // A4

TOP      nothing stated                       → OPEN_TOP                    // E6
         spout filling / inlet spout / a diameter mentioned → TOP_PANEL + spout
         skirt · duffle · top flap            → only when explicitly confirmed

FAMILIES TO SUPPORT — all twelve, no v1 subset                              // A5
  u_panel · circular · four_panel · four_panel_baffle · two_panel
  single_loop · two_loop · omega · tunnel · tubular · h_bottom · container_liner
```

## 3.2 Weight formulas

| # | Applies to | Formula |
|---|---|---|
| W1 | Fabric components | `weight_g = GSM × width_cm × cut_cm × qty / 10000` |
| W2 | Tape / loop / tie / cord | `weight_g = GPM × cut_cm × qty / 100` |
| W3 | LDPE liner | `effective_gsm = micron × 1.84`, then W1 |

## 3.3 Geometry — all from EXTERNAL dimensions (B2 confirmed)

| Family | Component | Rule | Qty | Corpus |
|---|---|---|---|---:|
| **U-panel** | Body | width = `W + 8`, cut = `2H + L + 8` ⚠️ *disputed §2①* | 1 | 94% / 7% |
| | Side | `(L + 8) × (H + 8)` | 2 | ✅ 94% / 98% |
| | Bottom | **none** — the U-piece forms it | — | ✅ confirmed |
| | Reinforcement | **none** — corner loop needs no RF | — | ✅ confirmed |
| **Circular** | Body | flat width = `W + L` (tube, no allowance), cut = `H + 8` | 2 walls | ✅ confirmed |
| | Top / Bottom | `(L + 10) × (W + 10)` — +10 because internal = external here | 1 | ✅ 86% / 81% |
| | Side | **none** | — | ✅ confirmed |
| **4-panel baffle** | Body | width = `W + 8`, cut = `H + 8` | 4 | 64% / 57% |
| | Top / Bottom | `(L + 8) × (W + 8)` — +8 because internal ≠ external | 1 | 61% |
| | Baffle | GSM `15+90+15`, both-side laminated | 4 | ✅ 100% |
| **Double layer** | Body + Side | 2 body fabrics **and** 2 side fabrics per side | ×2 | ✅ confirmed |

> **Fabric width is NEVER snapped to a loom width.** The loom is set to the calculated figure. (B6)

## 3.4 Spouts and closures — fully specified, and they verify

```
// Stated size is always DIAMETER × HEIGHT. First number = diameter, always.  B7

cut_length   = diameter × 3.14 + 12          FS 94.5% · DS 93.4% within 1.5 cm (n=311)
FS width     = height + 5
DS width     = height + 8

// Closure adds to the WIDTH, and determines the tie.  B8
open          extra fabric  0                    tie   none
tied          extra fabric  height + 8           tie   125 cm (standard)
iris          extra fabric  diameter / 2 + 6     tie   diameter × 3.14 + 38   ×2 ties
                                                        // 38 = 10+10 outside + 9+9 knots
petal         extra fabric  same as base         tie   diameter × 3.14 + 38
                                                        // also fits DS FLAP + DS PATCH
pyjama        extra fabric  diameter + 6         tie   none additional
                                                        // = spout + iris + iris, three layers

// A tie is MANDATORY wherever an FS, DS or Skirt exists, top or bottom.  E1
// "rope" is a DIFFERENT component from "tie" — do not merge them.        E1
```

## 3.5 Loops and belt

```
loop_cut  = 2 × free_height + LL + SL        // 197/226 = 87.2% exact
loop_qty  = 4
weight    = GPM × cut_cm × qty / 100

// Defaults when the customer does not state them.  D1
free_height  default 25 cm
LL           default 65% of bag height
SL           default 35% of bag height

// Belt selection.  D2
belt_width   default 50 mm unless the client specifies
             if computed belt weight < 25 g  →  drop to 40 mm

// Belt strength.  D5 — needs the ×2-legs confirmation, see §2③
capacity_kg  = GPM × 35 × loop_qty [× 2 legs?]     must be >= SWL × SF

// Optional loop hardware — ONLY when the customer asks.  D4
loop protector · extra loop · stevedore · full running loop
```

## 3.6 GSM policy

```
// C9 — component GSM relationships
bottom_gsm    = body_gsm                       // generally, all families
if bag_weight >= 2.5 kg:
    top_gsm = bottom_gsm = body_gsm
baffle_gsm    = 15 + 90 + 15  (= 120, both-side laminated)
spout_gsm     = 70 + 20       (= 90)
heavy-duty    → higher GSM per client requirement

// C7, C8 — how GSM is written on the sheet
the GSM column always holds the TOTAL, never the base
"70+20 LAMINATED"      → GSM column reads 90
"15+90+15"             → both-side lamination, 120 total
"175+30 UNLAMINATED"   → CLERICAL ERROR. It IS laminated. Fix on ingest.

// C4 — SWL band boundaries are exclusive
751–1000 · 1001–1250 · …          // SWL exactly 1000 falls in 751–1000

// C5 — choosing inside a chart range
the deciding factor is BAG WEIGHT. Drop to the lower end of the band to bring
the bag under a target. e.g. 240 gsm gives 3.1 kg → use 230 to hit 3.0.

// C6 — the customer overrides the chart
if the customer states a GSM below the chart minimum → proceed as they asked
                                                       and RAISE A WARNING,
                                                       not a rejection
```

## 3.7 Components, stitching, dust-proofing

```
// E4 — three dust-proof grades
1. filler cord / dust-proof     // "filler cord" is an alias for dust-proof
2. double dust proof (DDP)
3. triple dust proof            // = double dust proof + FELT

// E3 — DDP is DOUBLE DUST PROOF, not a discharge port
DDP weight = total_seam_length_m × 2 × 4.5 g/m
             // ×2 because double. The old qty-100 anomaly was cm read as metres.

// E2 — the rare components, all client-specified
FELT          triple dust-proof bags only
GLUE          liner glued to the bag
TABBING       liner tabbed at 4 or 8 points — the alternative to gluing
BELLY BAND    "stomach belt"
TOP BAND      an attachment
DS FLAP · DS PATCH   petal closures only

// E5, E7 — no accessory is ever added silently
liner · doc pocket · printing   →  only when the customer specifies
liner insertion default          →  loose
liner micron / method            →  client-specified, never assumed

// F1 — sewing yarn, a per-family constant  (baffle + single_loop disputed, §2②)
u_panel 45 g · circular 60 g · single_loop 35 g · baffle 72 g

// F2, F3, F4 — stitching and folding
overlock + chain  ==  HR + DR                // same thing, and the default
double needle / double chain                  // client-specified only
single fold                                   // the standard
out-fold == butterfly                         // the DEFAULT fold. NOT J-fold.
J-fold                                        // an alternative to out-fold/butterfly
"box J fold" and "top hemming"                // do not exist at Anjani — ignore in corpus

yarn white  3000–3200 DNR   safety stitching   // default
yarn blue   3600 DNR        Hirakal overlock
```

## 3.8 Component aliases — confirmed by E1

| Canonical | Raw labels |
|---|---|
| DISCHARGE SPOUT | `D/S` · `D SPOUT` · `DS SPOUT` · `DISCHARGE SPOUT` · `BOTTOM SPOUT` · `D/ SPOUT` · **`OUTLET SPOUT`** (added by engineer) |
| FILLING SPOUT | `FILLING SPOUT` · `FS SPOUT` · `F/S` · `TOP SPOUT` · `TOP / FS` — **but NOT `TOP SKIRT`, which is a separate attachment** |
| TIE | all tie aliases merge; **mandatory wherever FS, DS or Skirt exists** |
| IRIS TIE | `TIE/IRIS ROPE` · `IRISH TIE` · `TIE/IRIS` — same thing |
| ROPE | **a DIFFERENT component. Do not merge with tie.** |

---
---

# 4 · The architecture, final

```
                         ┌──────────────────────────────────────┐
                         │ 0 · INGEST                           │
                         │ WhatsApp · email · PDF TDS · scan→OCR│
                         └──────────────────┬───────────────────┘
                                            ▼
                         ┌──────────────────────────────────────┐
                         │ 1 · EXTRACTION — QWEN ADAPTER A      │  ← model
                         │ → OrderSpec incl. product_contents,  │
                         │   belt_width. Missing stays missing. │
                         └──────────────────┬───────────────────┘
                                            ▼
                         ┌──────────────────────────────────────┐
                         │ 2 · DERIVE + CLASSIFY                │
                         │ SWL from density × volume if absent  │
                         │ family from belt width · loop · top  │
                         └──────────────────┬───────────────────┘
                       ┌────────────────────┼────────────────────┐
                       ▼                                         ▼
        ┌──────────────────────────┐              ┌──────────────────────────┐
        │ 3 · RETRIEVAL            │              │ 4 · RULE ENVELOPE        │
        │ top-3, weighted by       │              │ GSM band · belt band     │
        │ product + geometry       │              │ mandatory components     │
        └──────────────┬───────────┘              └───────────┬──────────────┘
                       └────────────────────┬────────────────────┘
                                            ▼
                         ┌──────────────────────────────────────┐
       ┌──── SOLVER ────▶│ 5 · CONFIGURATION — QWEN ADAPTER B  │  ← model
       │                 │ → BuildSpec · ~70 closed decisions   │
       │                 │ no widths · no cuts · no weights     │
       │                 └──────────────────┬───────────────────┘
       │                                    ▼
       │                 ┌──────────────────────────────────────┐
       │                 │ 6 · RENDERER — deterministic         │
       │                 │ geometry → quantities → weights      │
       │                 │ NO loom snapping (B6)                │
       │                 └──────────────────┬───────────────────┘
       │                                    ▼
       │                 ┌──────────────────────────────────────┐
       │  knobs in order │ 7 · WEIGHT SOLVER                    │
       │  1. loop GPM    │ target given → backward              │
       │  2. loop cut    │ absent       → forward from SWL/SF   │
       │  3. body GSM    │ ±2% · max 3 passes                   │
       └─────────────────┴──────────────────┬───────────────────┘
                                            ▼
                         ┌──────────────────────────────────────┐
                         │ 8 · VALIDATION GATE                  │
                         │ recompute every line                 │
                         └──────────────────┬───────────────────┘
                                            ▼
                         ┌──────────────────────────────────────┐
                         │ 9 · DUAL OUTPUT                      │
                         │ BOM sheet  +  CLARIFICATION LIST     │
                         │ construction shown FIRST (H5)        │
                         └──────────────────────────────────────┘
```

**Changes from the previous draft:** loom-width snapping deleted (B6); SWL derivation from bulk density added (G6); the solver's knob order reversed to loop-first (G3); and the clarification list promoted to a co-equal output, because the answers to G2 and G5 say the real job is asking the client the right question, not deciding alone.

## 4.1 The decision algorithm, exactly

```
STEP 1 — establish the load
  if SWL stated                        → use it
  elif product_contents AND volume     → SWL = volume_m³ × bulk_density(product)   // G6
                                          bulk density from the National Bulk Bag table
  else                                 → CLARIFY: "SWL or product + fill volume required"
  if SF absent                         → CLARIFY: "single-trip (5:1) or multi-trip (6:1)?"

STEP 2 — classify   family, loop type, top, bottom          // deterministic, §3.1

STEP 3 — choose the mode                                     // C2
  target_weight stated  →  BACKWARD   solve for a build that lands within ±2%
  target_weight absent  →  FORWARD    GSM from chart, belt from chart, report weight

STEP 4 — BACKWARD mode, knobs in the engineer's order        // G3
  pass 1   adjust loop GPM        within the belt band, honouring capacity >= SWL×SF
  pass 2   adjust loop cut        via free height / LL / SL, within observed ranges
  pass 3   adjust body GSM        only within market-standard values for the load
  still outside ±2%  →  do NOT force it. Emit both options and CLARIFY.  // G2

STEP 5 — the customer-override rule                          // C6
  customer stated a GSM below the chart minimum
      → build at the stated GSM
      → emit a WARNING, not a rejection
      → add to clarification list: "GSM {x} is below our {y} standard for
         SWL {swl} at {sf}. Confirm you want us to proceed."

STEP 6 — the conflict case (the 85×85×85 enquiry)            // G2
  target weight and stated GSM cannot both hold
      → compute BOTH builds
      → present both, with the weight and the GSM each implies
      → CLARIFY: "proceed against bag weight, or against the specified GSM?"
```

### Correction to the earlier report

My earlier report called the 720 g enquiry **"infeasible"**. With C6 and G2 answered, that was too strong. The correct behaviour is: build both — 878 g at the customer's 150 GSM, and ~112 GSM if 720 g is the binding constraint — state that 112 GSM is below the 140 GSM standard for SWL 1000 at 5:1, and **ask which one they want**. The system does not refuse and does not silently pick. It presents the trade and requests a decision.

## 4.2 The validation gate

| Check | Rule | Severity |
|---|---|---|
| Arithmetic | every component weight recomputed from its own geometry | **reject + repair** |
| Grand total | equals the sum of component weights | **reject** |
| Mandatory set | family's required components present, no phantom parts | **reject** |
| Phantom bottom | U-panel must have **no** bottom panel and **no** RF | **reject** |
| Tie presence | FS, DS or Skirt present ⇒ a tie must exist (E1) | **reject** |
| Belt capacity | `GPM × 35 × qty [× 2] ≥ SWL × SF` (D5) | **reject** |
| Spout geometry | cut = D×3.14+12; width per closure rule | **reject + repair** |
| GSM vs chart | below the band **and** customer did not state it | **reject** |
| GSM vs chart | below the band **and** the customer stated it (C6) | ⚠️ warn + clarify |
| Weight vs target | outside ±2% (G1) | ⚠️ warn + clarify |
| Safety factor | 5:1 single-trip only; 6:1 required for multi-trip / UN | ⚠️ warn if reuse implied |
| Static type | Type A only for non-flammable; Type C must be groundable | ⚠️ warn if contents suggest otherwise |
| Line-level diff | every line compared against the nearest retrieved bag | advisory |
| Construction first | output leads with family + loop type (H5) | presentation |

The last row is not decoration. Asked what he would check to trust a generated BOM in ten seconds, the engineer said: *"first and foremost the bag construction type… if the bag type is chosen correctly then the weight of the bag along with the GSM taken."* So the output leads with construction, then weight and GSM, then everything else. **That ordering is a requirement.**

---
---

# 5 · Data preparation and fine-tuning

The plan from the previous report stands. Three amendments follow from the answers.

### 1 · OrderSpec gains the field that explains everything

`product_contents` — free text, plus a derived `bulk_density_kg_m3` when the product matches the National Bulk Bag table. This is the answer to C1, and without it the model cannot learn why one 90×90×110 bag was 125 GSM and another 210. It also feeds retrieval: two bags for the same product should rank closer than two bags of the same size for different products.

### 2 · Deduplicate by content, per H1

He was explicit: *"Do not learn from duplicates."* Content-hash the workbooks first — `DOMESTIC ENQUIRY.xlsx` appears in two locations, `EXPORT ENQUIRY.xlsx` in three — then collapse identical (input, output) pairs, then fingerprint-group the split.

### 3 · A third training target: the clarification list

G5 asks for the agent to identify what is missing and raise it. That is a generated output, so it needs supervision. It is derivable for free: for every historical sheet, compute which OrderSpec fields were `not_specified`, and emit the questions the rule book says are needed for those gaps. ~395 rows, zero labelling, and it makes "ask, don't guess" trainable rather than hoped-for.

## 5.1 Final training data plan

| Adapter | Rows | Source | Effort |
|---|---|---|---|
| **A — extraction** | ~1,300 verified synthetic | enquiry prose rendered from `OrderSpec_gold`, round-trip verified | 3 days |
| | ~200 hard negatives | hand-constructed: two size triples, negations, imperial units, TDS style | 1 day |
| | **~30 real, EVAL ONLY** | SPEC JIEXP PDFs, COMPONENT sheets, scans — **never trained on** | 1 day |
| **B — configuration** | **395 real** | `OrderSpec_gold` + retrieved + envelope → `BuildSpec_gold` | **zero** |
| | ~1,200 solver-feedback | perturb loop GPM then GSM, render, train it back — **in the engineer's knob order** | 1 day |
| | ~200 conflict cases | target vs stated GSM contradictions → correct output is a clarification, not a build | 1 day |
| **C — clarification** | ~395 | derived from which OrderSpec fields were absent | **zero** |

Adapter C is small enough to fold into adapter B as a second output field rather than a third LoRA — decide after measuring.

## 5.2 The three data contracts

- **`OrderSpec`** — what the customer said. Built from the **header block alone** (a structural firewall, enforced in code). Every field carries `{value, state, evidence_span}` so hallucination is measurable, not a matter of opinion.
- **`BuildSpec`** — what the engineer decided. ~70 fields, every one an enum, boolean, or catalogue value. **Not one is a computed quantity.**
- **`PhysicalBOM`** — what gets cut. Produced entirely by code. Used only to test the renderer, never as a training target.

## 5.3 Fine-tuning configuration

| Setting | Adapter A | Adapter B |
|---|---|---|
| base | `Qwen3-4B-Instruct` (Apache 2.0) | same |
| method | LoRA, **bf16** (not QLoRA) | same |
| rank `r` | 16 | 32 |
| `lora_alpha` | 32 | 64 |
| `lora_dropout` | 0.05 | 0.05 |
| target modules | `q_proj k_proj v_proj o_proj gate_proj up_proj down_proj` | same |
| learning rate | 2e-4 | 1e-4 |
| scheduler | cosine, `warmup_ratio 0.03` | same |
| epochs | 2 | 3 |
| batch | `per_device 2`, `grad_accum 4` → effective 8 | same |
| `max_seq_length` | 2048 | **4096** (three retrieved BuildSpecs in prompt) |
| loss | completion-only, prompt masked | same |
| wall clock | under an hour | under an hour |

Serve under **vLLM + XGrammar** with the JSON Schema generated from the Pydantic model as `guided_json`. This makes a structurally invalid or out-of-enum answer *impossible to emit*, not merely unlikely. Watch training loss settle in the **0.5–1.0** band; approaching zero means memorisation.

## 5.4 Ship gates

| Layer | Metric | Gate |
|---|---|---|
| Adapter A | **Hallucination rate** (fields asserted whose evidence span is absent) | **< 2%** on `eval_real` |
| | Exact match on numerics | > 95% |
| | Accuracy on enums | > 92% |
| Adapter B | Body GSM exact match | > 55% |
| | Body GSM within one catalogue step | > 85% |
| | Component set F1 | > 0.96 |
| End to end | Median bag-weight error | **< 2%** |
| | Share inside ±2% of target | **> 70%** |
| | Geometry within 2 cm | > 90% per component |
| | **GSM floor violations with no customer override** | **zero, always** |
| Safety | Conflict cases correctly routed to clarification | 100% |
| | Solver converges within 3 passes | > 90% |

**Four baselines that must be beaten:** the rule engine alone; rule engine + retrieval; **base Qwen3-4B few-shot under the same grammar** (run this in week one — it costs nothing and is often startlingly close); and the current regex normaliser.

---
---

# 6 · What is still needed

## From the engineer — five short questions

1. **The +8 / +10 conflict (§2①).** His rule predicts +8 in cells where the corpus uses +10 on 72% and 93% of bags. Which governs going forward?
2. **Baffle and single-loop yarn (§2②).** Stated 72 g and 35 g; corpus medians are 100 g and 25 g.
3. **Belt capacity (§2③).** Does each corner loop count as two load-bearing legs? At ×4 the rule fails on 61% of bags; at ×8 it works.
4. **The U+2 GSM table (C3).** He said a fresh one will be prepared. Until it exists, U-panel — 44% of all bags — has no chart, and the forward mode cannot run for it.
5. **Two referenced documents not in this folder:** the **belt strength sheet** (D5) and the **liner cut-size formula** (E7), both described as "already shared".

## Two operational asks — still the highest-value items

- **Keep the next twenty raw enquiries.** He agreed to try. This is the only training data that cannot be reconstructed, and every week without it is a week lost.
- **Have him narrate one enquiry end to end**, including the decisions he makes without noticing. Several of the four conflicts above would likely dissolve in five minutes of listening.

---
---

# 7 · Build order

Nothing before step 6 needs a GPU, and steps 1–4 alone should take median weight error under 3%.

| # | Step | Effort |
|---|---|---|
| 1 | **Rule registry from the answers.** Every confirmed rule in §3 becomes JSON with source, rule level and corpus agreement attached. The four disputed rules go in flagged `needs_confirmation` and **fail loudly** rather than silently picking a side. | 2 days |
| 2 | **Renderer, tested against all 395 sheets.** Feed each sheet's own BuildSpec in; output must equal its component table. Spout formulas should reproduce at ~94% immediately. | 4 days |
| 3 | **Classifier, SWL derivation, envelope.** Deterministic family/loop/top rules, the bulk-density lookup, GSM and belt bands. Digitise the National Bulk Bag density table (28 pp: product name, lbs/ft³, g/cm³). | 3 days |
| 4 | **Solver in the engineer's knob order, plus the clarification engine.** Loop GPM → loop cut → body GSM. Both modes. The conflict path that emits two builds and a question. Measure against the 350 sheets that state a target weight. | 4 days |
| 5 | **Gold layers, firewall, dedup, fingerprint split.** OrderSpec from the header block alone, enforced structurally. Content-hash dedup per H1. Zero-leakage assertion in the test suite. | 4 days |
| 6 | **Adapter B, then adapter A.** B first — its data is already real and complete. A second, gated hard on hallucination rate against the ~30 real documents. | 6 days |
| 7 | **Output writer and audit.** Four-block sheet, construction type first, then weight and GSM. Per-field provenance. Clarification list as a co-equal deliverable. | 3 days |
| 8 | **Shadow run.** Generate a BOM for every real enquiry alongside the engineer, without showing him until he has finished his own. Every disagreement is either a bug or a rule nobody has written down — both worth more than further training. | one month |

---

## In one paragraph

The BOM agent reads an enquiry in any format and extracts only what the customer actually said. It derives the load from bulk density if the customer gave a product and a volume instead of an SWL. It classifies the construction by fixed rule — U+2 unless a belt of 70 mm or more says circular. A fine-tuned Qwen adapter then makes roughly seventy engineering decisions from a closed vocabulary, informed by the three nearest bags Anjani has actually built and the chart bands for this load. Deterministic code turns those decisions into every number on the sheet. If the customer named a target weight, a solver adjusts loop gramage, then loop cut length, then body GSM until the bag lands within ±2%. A gate recomputes every line and refuses anything structurally wrong. And where the enquiry contradicts itself, or the chart, or physics, the agent does not decide alone — it builds both options and hands the engineer the exact question to put to the customer. That last behaviour is the one the engineer asked for by name, and it is what separates a calculator from something worth trusting.

---

*End of report.*
