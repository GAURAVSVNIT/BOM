# Architecture And Build Order

## Target Architecture

```text
Customer Query (Hindi/English/Mixed)
  -> NLP Extractor (Sarvam)
  -> StructuredSpec
  -> Rule Engine + Hybrid Retrieval
  -> Deterministic PhysicalBOM + Top-3 RetrievedBOMs
  -> LLM Synthesis
  -> Validation Gate
  -> Retry or FinalBOMPackage
```

## Module Boundaries

### 1. NLP Extractor

Input: `CustomerQueryRaw`

Output: `StructuredSpec`

Responsibilities:

- Extract intent from Hindi/English/mixed text.
- Normalize units to cm/g/kg.
- Mark missing SWL/SF as `not_specified`, not as error.
- Do not choose engineered component GSM/cut/weight.

### 2. Normalization Layer

Input: raw StructuredSpec draft

Output: normalized StructuredSpec

Responsibilities:

- Canonicalize bag type and component vocabulary.
- Parse `5:1`, `05:01`, `5`, `SF 5`.
- Parse target weight in gram/kg strings.
- Infer internal/external dimensions only with explicit rule and audit note.

### 3. Rule Engine

Input: `StructuredSpec`

Output: deterministic `PhysicalBOM`

Responsibilities:

- Determine mandatory components.
- Choose minimum legal GSM from rule tables.
- Choose loom widths from approved table only.
- Compute cut dimensions and weights.
- Produce complete conservative BOM without LLM/retrieval.
- Record assumptions, constraint inputs, and rule hits.

### 4. Hybrid Retrieval

Input: normalized `StructuredSpec`

Output: top-3 `RetrievedBOM`

Scoring blocks:

- Geometric: dimensions, SWL, SF, target weight.
- Categorical: bag_type, top/bottom, baffle, liner, doc, DDP, printing, loop family.
- Semantic: raw phrasing, customer notes, accessory descriptions.

Retrieval returns structured examples, not text chunks.

### 5. LLM Synthesis

Input:

- StructuredSpec
- deterministic PhysicalBOM
- top-3 RetrievedBOMs
- rule table summary
- exact output schema
- hard constraints

Output: schema-valid raw PhysicalBOM plus rationale fields.

Allowed:

- choose between close alternatives from deterministic and retrieval evidence
- fill optional components when supported
- reconcile target vs actual practical BOM
- normalize edge-case vocabulary

Forbidden:

- invent loom widths
- choose GSM below threshold
- add forbidden components
- omit mandatory components
- output prose instead of JSON

### 6. Validation Gate

Runs after rule engine and after LLM synthesis.

Hard validations:

- schema valid
- no forbidden component names
- no missing mandatory components
- loom widths in table
- GSM in allowed/minimum table
- GSM not below design threshold
- valid lamination values
- weight formulas consistent
- generated computed total equals actual
- legal top/bottom/accessory combination

Soft validations:

- target vs actual weight gap > 10 percent
- unusual component mix
- rare loop length or width
- retrieval disagreement
- low extractor confidence

### 7. Retry Loop

Max two retries.

Retry 1: fix only validation errors.

Retry 2: choose from allowed values only; do not alter valid fields.

Final fallback: deterministic BOM with warnings and audit trail.

## Sprint Plan

### Sprint 1

Deliver contracts and rule tables only.

Done when:

- Object contracts are frozen.
- Canonical components are frozen.
- Static rule tables exist.
- One paper example exists.

### Sprint 2

Implement:

- NLP extractor interface stub
- normalization layer
- deterministic rule engine
- validation gate for deterministic output only

Done when:

- System can produce a legal BOM without any model.

### Sprint 3

Implement:

- geometric index from corrected CSV
- semantic index from JSON instruction/spec text
- hybrid scoring
- structured top-3 retrieval output

Done when:

- Retrieval returns explainable structured examples for test specs.

### Sprint 4

Implement:

- LLM synthesis prompt
- retry loop
- audit trail
- CSV/XLSX package output

Done when:

- FinalBOMPackage is generated and validated end-to-end.

