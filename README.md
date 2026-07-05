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
                                        (normalize + compare)
                                                  │
                            reference_data.py ────┤  ground-truth notes per field
                          (HS nomenclature, UN/LOCODE,
                           carrier prefix, ISO 6346)
                                                  │
                                                  ▼
                        📋 report (CLI)   ·   🌐 web UI (main.py + FastAPI)
```

`pipeline.py` is the orchestrator; `main.py` serves the same result as a web page.

## Features

- **PDF → structured fields** using an LLM (Groq's free Llama 3.3 70B). Fields are extracted by the model at run time. An optional **replay mode** re-uses the JSON cached from your last real run for fast, offline, repeatable checks.
- **Smart normalization** so formatting noise doesn't create false mismatches:
  - weights compare numerically (`"12,000 KG"` == `12000`)
  - package counts compare as integers (`"430 CARTONS"` == `430`)
  - missing fields (`null`) are treated as absent, not as empty strings
- **Preserves real differences** — e.g. same consignee company but a different address is flagged, not hidden.
- **Two axes of validation per field:**
  - *Cross-document* — do the documents agree with each other? (`AGREE` / `MISMATCH` / `SINGLE`)
  - *Ground-truth* — is the value real? (`reference_data.py`): ISO 6346 container check-digit, HS code looked up in the Harmonized System nomenclature, port checked against the complete UN/LOCODE list (~110k locations, seaport-aware), B/L number matched to its carrier prefix.
- **Clean, readable CLI report** plus a **FastAPI web UI** (`main.py`) where you **upload your own PDFs** (or load the bundled samples) and see every field with its status badge, the ground-truth note underneath, and mismatches expanded with the actual differing values.

## Project structure

| File | Responsibility |
|------|----------------|
| `extract.py` | Read a PDF, prompt the LLM, parse the JSON of extracted fields. In replay mode, re-reads the last real extraction instead of calling the LLM. |
| `reconcile.py` | Normalize and compare fields across documents; attach ground-truth notes; print the report. |
| `reference_data.py` | Knowledge base: HS-code lookup (`pyhscodes`), UN/LOCODE port check, carrier-prefix check, and the ISO 6346 wiring. |
| `validation.py` | Standalone ISO 6346 container check-digit implementation. |
| `pipeline.py` | Orchestration: extract all three PDFs → save → reconcile. `run()` is shared by the CLI and the web UI. |
| `main.py` + `templates/` | FastAPI web UI rendering the reconciliation as an HTML page. |
| `data/code-list.csv` | The complete UNECE UN/LOCODE code list (~110k locations), used by the port check. |
| `samples/` | The three sample PDFs and `extracted_live.json` — the extraction cached from the last real run (also what replay mode reads). |

## Setup

```bash
pip install -r requirements.txt
```

Get a **free** Groq API key at [console.groq.com/keys](https://console.groq.com/keys) (no credit card required) and add it to a `.env` file in the project root:

```
GROQ_API_KEY=gsk_your_key_here
```

## Usage

**Live CLI** — extract the real PDFs with the LLM and reconcile:

```bash
python pipeline.py
```

**Web UI** — upload your own PDFs (one per document slot) and reconcile, or click **Use sample documents** to try the bundled set:

```bash
uvicorn main:app --reload
# then open http://127.0.0.1:8000
```

**Replay mode** — re-uses `samples/extracted_live.json`, the real AI extraction cached from your last live run (no LLM call, no cost). Handy for offline/repeatable runs. Set `BL_RECONCILER_REPLAY` to force it, for either the CLI or the web UI:

```bash
# PowerShell
$env:BL_RECONCILER_REPLAY='1'; python pipeline.py
# bash
BL_RECONCILER_REPLAY=1 python pipeline.py
```

> Live mode requires `GROQ_API_KEY` in the environment (or `.env`). `BL_RECONCILER_REPLAY` overrides it and replays the cached extraction instead — a dedicated flag is needed because simply clearing `GROQ_API_KEY` doesn't work when it's stored in `.env`, since `load_dotenv()` reloads it. Replay needs at least one prior live run to have produced the cache.

## Sample output

```
================ SHIPMENT RECONCILIATION ================
[ . ] bl_number            SINGLE    [INVALID]
        - CBSUSG774120558  [!! Unrecognised carrier prefix 'CBSU']
[XX ] container_no         MISMATCH  [INVALID]
        - Bill of Lading        : CBSU7392104  [OK ISO 6346 check digit valid]
        - Shipping Instruction  : CBSU7392014  [!! ISO 6346 check digit INVALID - stated 4, computed 7]
        - VGM Certificate       : CBSU7392104  [OK ISO 6346 check digit valid]
[OK ] seal_no              AGREE
[XX ] consignee            MISMATCH
        - Bill of Lading        : SOUTHERN HOME LIVING PTY LTD ... Port Melbourne, Victoria 3207
        - Shipping Instruction  : SOUTHERN HOME LIVING PTY LTD ... Dandenong, Victoria 3175
[OK ] vessel_name          AGREE
[OK ] voyage_no            AGREE
[OK ] port_of_discharge    AGREE     [VALID]
        - MELBOURNE  [OK UN/LOCODE AUMEL (Melbourne, AU) - seaport]
[XX ] gross_weight         MISMATCH
        - Bill of Lading        : 13,480.00
        - Shipping Instruction  : 13,480.00
        - VGM Certificate       : 14,000
[OK ] hs_code              AGREE     [VALID]
        - 9403.60  [OK HS 940360: Furniture; wooden, other than for office, kitchen or bedroom use]
[OK ] package_count        AGREE
[ . ] vgm_kg               SINGLE
--------------------------------------------------------
3 mismatch(es) and 2 validation error(s) across 11 fields.
========================================================
```

> The `container_no` line shows the two axes working independently: the reads **MISMATCH** across documents (the Shipping Instruction has `...014` instead of `...104`) *and* that mistyped read is **INVALID** by ISO 6346, while the other two are valid. Crucially, agreement and validity are separate — if all three documents had *agreed* on a number with a bad check digit, it would still be flagged `AGREE [INVALID]`, because agreeing on a wrong value is not the same as being correct. `consignee` shows a mismatch with no validity axis: same company, different address — a real conflict with no external "ground truth" to check against. And `bl_number` is `[INVALID]` here because these fictitious samples use an invented carrier prefix (`CBSU`) that isn't a registered shipping line.

Reading the verdicts — each field has up to **two independent** verdicts:

**Axis 1 — cross-document agreement** (always shown):

| Icon | Verdict | Meaning |
|:---:|---|---|
| `OK ` | `AGREE` | All documents that carry this field match. |
| `XX ` | `MISMATCH` | Documents disagree — values are listed for inspection. |
| ` . ` | `SINGLE` | Only one document carries this field. |

**Axis 2 — validity** (shown only for fields with a ground-truth check: `container_no`, `bl_number`, `port_of_discharge`, `hs_code`):

| Verdict | Meaning |
|---|---|
| `[VALID]` | The value passes its real-world check (check digit / dataset / format). |
| `[INVALID]` | The value fails it — a genuine error, **independent of whether the documents agree**. |

The summary counts them separately: *"N mismatch(es) and M validation error(s)"*.

## Extracted fields

`bl_number` · `container_no` · `seal_no` · `consignee` · `vessel_name` · `voyage_no` · `port_of_discharge` · `gross_weight` · `hs_code` · `package_count` · `vgm_kg`

---

<sub>Prototype for automated shipping-document reconciliation. Extraction is non-deterministic (LLM-based), so live results can vary run to run; use replay mode to re-check the last real extraction without re-calling the model.</sub>
