# 📦 B/L Reconciler

> Cross-check shipping documents automatically. Extract the key fields from each PDF, compare them side by side, and flag the discrepancies that matter.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white">
  <img alt="LLM" src="https://img.shields.io/badge/LLM-Groq%20Llama%203.3-F55036?logo=meta&logoColor=white">
  <img alt="Standard" src="https://img.shields.io/badge/ISO%206346-check%20digit-2E7D32">
  <img alt="Status" src="https://img.shields.io/badge/status-prototype-blue">
</p>

---

## What it does

A shipment is described by several documents: a **Bill of Lading**, a **Shipping Instruction**, and a **VGM Certificate** - that *should* all agree on the container number, weight, consignee, vessel, and so on. In practice they don't, and catching the mismatches by eye is slow and error-prone.

**B/L Reconciler** reads all three PDFs, pulls out the same set of fields from each, and produces a single reconciliation report that tells you - field by field - whether the documents **AGREE**, **MISMATCH**, or only appear in one document (**SINGLE**). Container numbers are additionally validated against the **ISO 6346** check-digit standard, so a bad read can be told apart from a genuine document conflict.

## How it works

```
  Sample_Bill_of_Lading.pdf ─┐
  Sample_Shipping_Instr.pdf ─┼─▶  extract.py   ──▶  { doc: { field: value } }
  Sample_VGM_Certificate.pdf ┘   (PDF → fields                │
                                  via Groq LLM)               │  saved to
                                                              ▼  samples/extracted_live.json
                                             reconcile.py  ◀──┘
                                        (normalize + compare,
                                         ISO 6346 validation)
                                                  │
                                                  ▼
                                        📋  reconciliation report
```

`pipeline.py` is the orchestrator that ties the three modules together.

## Features

- **PDF → structured fields** using an LLM (Groq's free Llama 3.3 70B), with a deterministic **mock mode** for offline/repeatable runs.
- **Smart normalization** so formatting noise doesn't create false mismatches:
  - weights compare numerically (`"12,000 KG"` == `12000`)
  - package counts compare as integers (`"430 CARTONS"` == `430`)
  - missing fields (`null`) are treated as absent, not as empty strings
- **Preserves real differences** — e.g. same consignee company but a different address is flagged, not hidden.
- **ISO 6346 container check-digit validation** — every `container_no` is validated, so an OCR/extraction error is distinguishable from a true document conflict.
- **Clean, readable report** with `AGREE` / `MISMATCH` / `SINGLE` verdicts and per-document values for anything that disagrees.

## Project structure

| File | Responsibility |
|------|----------------|
| `extract.py` | Read a PDF, prompt the LLM, parse the JSON of extracted fields. Falls back to mock data when no API key is set. |
| `reconcile.py` | Normalize and compare fields across documents; run the check-digit validation; print the report. |
| `validation.py` | Standalone ISO 6346 container check-digit implementation. |
| `pipeline.py` | Orchestration: extract all three PDFs → save → reconcile → report. |
| `samples/` | The three sample PDFs, hand-typed mock data (`extracted.json`), and the generated live output (`extracted_live.json`). |

## Setup

```bash
pip install groq pypdf python-dotenv
```

Get a **free** Groq API key at [console.groq.com/keys](https://console.groq.com/keys) (no credit card required) and add it to a `.env` file in the project root:

```
GROQ_API_KEY=gsk_your_key_here
```

## Usage

**Live** — extract the real PDFs with the LLM and reconcile:

```bash
python pipeline.py
```

**Mock mode** — no API key needed; reads the hand-typed `samples/extracted.json`. Deterministic, so it doubles as a regression test:

```bash
# PowerShell
$env:GROQ_API_KEY=''; python pipeline.py
# bash
GROQ_API_KEY= python pipeline.py
```

> The live/mock switch is simply the presence of `GROQ_API_KEY` in the environment.

## Sample output

```
================ SHIPMENT RECONCILIATION ================
[XX ] container_no         MISMATCH
        - Bill of Lading        : MEDU7745120  [check digit INVALID]
        - Shipping Instruction  : MEDU7745102  [check digit INVALID]
        - VGM Certificate       : MEDU7745120  [check digit INVALID]
[OK ] seal_no              AGREE
[XX ] gross_weight         MISMATCH
        - Bill of Lading        : 11,560.00
        - Shipping Instruction  : 11,560.00
        - VGM Certificate       : 12000
[XX ] consignee            MISMATCH
        - Bill of Lading        : COMPLETE IMPORTS PTY LTD ... Brisbane, Queensland 4009
        - Shipping Instruction  : COMPLETE IMPORTS PTY LTD ... Townsville, Queensland 4814
[OK ] hs_code              AGREE
[OK ] package_count        AGREE
[ . ] bl_number            SINGLE
--------------------------------------------------------
4 mismatch(es) found across 10 fields.
========================================================
```

Reading the verdicts:

| Icon | Verdict | Meaning |
|:---:|---|---|
| `OK ` | `AGREE` | All documents that carry this field match. |
| `XX ` | `MISMATCH` | Documents disagree — values are listed for inspection. |
| ` . ` | `SINGLE` | Only one document carries this field. |

## Extracted fields

`bl_number` · `container_no` · `seal_no` · `consignee` · `vessel_voyage` · `port_of_discharge` · `gross_weight` · `hs_code` · `package_count` · `vgm_kg`

---

<sub>Prototype for automated shipping-document reconciliation. Extraction is non-deterministic (LLM-based), so live results can vary run to run; use mock mode for stable, repeatable checks.</sub>
