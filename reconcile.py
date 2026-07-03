import json
import re
from pathlib import Path

from validation import container_check_digit

# The 4 possible verdicts for a field
AGREE    = "AGREE"
MISMATCH = "MISMATCH"
SINGLE   = "SINGLE"
MISSING  = "MISSING"

def normalize(field_name: str, value: str) -> str:

    if field_name in ("gross_weight", "vgm_kg"):
        # keep only the numeric part: drop commas and any unit suffix like "KG"
        number=value.replace(",","").split()[0]
        return str(float(number))

    if field_name == "package_count":
        # compare on the integer count only, ignoring words like "CARTONS"
        digits=re.findall(r"\d+", value)
        return digits[0] if digits else value.strip().upper()

    cleaned=value.upper()
    for ch in "/,()":
        cleaned=cleaned.replace(ch, " ")
    cleaned=" ".join(cleaned.split()) 

    return cleaned


def reconcile(docs: dict) -> list:
    results=[]

    all_fields=set()
    for fields in docs.values():
        all_fields.update(fields.keys())

    for field in all_fields:
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

        result={"field":field, "status":status, "values":values}
        if field=="container_no":
            # ISO 6346 check digit tells us which reads are structurally valid,
            # separating a real document conflict from a bad OCR/extraction.
            result["validation"]={doc: container_check_digit(v)
                                  for doc, v in values.items()}
        results.append(result)

    return results


def load_docs(path: str = "samples/extracted.json") -> dict:
    return json.loads(Path(path).read_text())


def print_report(results: list) -> None:
    icon = {AGREE: "OK ", MISMATCH: "XX ", SINGLE: " . ", MISSING: " ? "}
    print("\n================ SHIPMENT RECONCILIATION ================")
    for r in results:
        print(f"[{icon.get(r['status'], '   ')}] {r['field']:20} {r['status']}")
        validation = r.get("validation")
        if validation:
            for doc, val in r["values"].items():
                ok, reason = validation[doc]
                tag = "valid" if ok else "INVALID"
                print(f"        - {doc:22}: {val}  [check digit {tag}]")
        elif r["status"] in (MISMATCH,):
            for doc, val in r["values"].items():
                print(f"        - {doc:22}: {val}")
    mism = sum(1 for r in results if r["status"] == MISMATCH)
    print("--------------------------------------------------------")
    print(f"{mism} mismatch(es) found across {len(results)} fields.")
    print("========================================================\n")

if __name__ == "__main__":
    docs = load_docs()
    results = reconcile(docs)
    print_report(results)
