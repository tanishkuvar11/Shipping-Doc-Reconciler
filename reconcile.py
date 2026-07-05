import json
import re
from pathlib import Path

from reference_data import field_note
from extract import TARGET_FIELDS

AGREE    = "AGREE"
MISMATCH = "MISMATCH"
SINGLE   = "SINGLE"
MISSING  = "MISSING"

def normalize(field_name: str, value: str) -> str:

    if field_name in ("gross_weight", "vgm_kg"):
        number=value.replace(",","").split()[0]
        return str(float(number))

    if field_name == "package_count":
        digits=re.findall(r"\d+", value)
        return digits[0] if digits else value.strip().upper()

    cleaned=value.upper()
    for ch in "/,()":
        cleaned=cleaned.replace(ch, " ")
    cleaned=" ".join(cleaned.split()) 

    return cleaned


def reconcile(docs: dict) -> list:
    results=[]

    seen=set()
    for fields in docs.values():
        seen.update(fields.keys())
    ordered=[f for f in TARGET_FIELDS if f in seen]
    ordered+=sorted(seen-set(ordered))

    for field in ordered:
        values={}
        for doc_name, fields in docs.items():
            if fields.get(field) is not None:
                values[doc_name]=fields[field]

        normalized=[normalize(field,v) for v in values.values()]
        if len(values)==1:
            status=SINGLE
        elif len(set(normalized))==1:
            status=AGREE
        else:
            status=MISMATCH

        notes={}
        for doc, v in values.items():
            note_status, note_text = field_note(field, v)
            if note_status is not None:
                notes[doc]=(note_status, note_text)

        result={"field":field, "status":status, "values":values}
        if notes:
            result["notes"]=notes

            result["valid"]=all(ok for ok, _ in notes.values())
        results.append(result)

    return results


def load_docs(path: str = "samples/extracted_live.json") -> dict:
    """Load a saved extraction (real AI output from a previous run)."""
    return json.loads(Path(path).read_text())


def _note_suffix(note) -> str:
    if not note:
        return ""
    ok, text = note
    tag = "OK" if ok else "!!"
    return f"  [{tag} {text}]"


def print_report(results: list) -> None:
    icon = {AGREE: "OK ", MISMATCH: "XX ", SINGLE: " . ", MISSING: " ? "}
    print("\n================ SHIPMENT RECONCILIATION ================")
    for r in results:
        validity = ""
        if "valid" in r:
            validity = "  [VALID]" if r["valid"] else "  [INVALID]"
        print(f"[{icon.get(r['status'], '   ')}] {r['field']:20} {r['status']}{validity}")
        notes = r.get("notes", {})
        if r["status"] == MISMATCH:
            for doc, val in r["values"].items():
                print(f"        - {doc:22}: {val}{_note_suffix(notes.get(doc))}")
        elif notes:
            doc, val = next(iter(r["values"].items()))
            print(f"        - {val}{_note_suffix(notes.get(doc))}")
    mism = sum(1 for r in results if r["status"] == MISMATCH)
    invalid = sum(1 for r in results if r.get("valid") is False)
    print("--------------------------------------------------------")
    print(f"{mism} mismatch(es) and {invalid} validation error(s) "
          f"across {len(results)} fields.")
    print("========================================================\n")

if __name__ == "__main__":
    docs = load_docs()
    results = reconcile(docs)
    print_report(results)
