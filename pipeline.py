import json
from pathlib import Path

from extract import extract_fields
from reconcile import reconcile, print_report

DOCUMENTS = {
    "Bill of Lading": "samples/Sample_Bill_of_Lading.pdf",
    "Shipping Instruction": "samples/Sample_Shipping_Instruction.pdf",
    "VGM Certificate": "samples/Sample_VGM_Certificate.pdf",
}


def reconcile_paths(documents: dict, save: bool = True, replay: bool = False):
    """Extract fields from a {label: pdf_path} map and reconcile.
    Returns (docs, results). Shared by the CLI, the sample run, and uploads.
    `replay=True` forces the cached real extraction (sample button)."""
    docs = {}
    for doc_name, pdf_path in documents.items():
        docs[doc_name] = extract_fields(pdf_path, doc_name, replay=replay)

    if save and not replay:
        Path("samples/extracted_live.json").write_text(json.dumps(docs, indent=2))

    results = reconcile(docs)
    return docs, results


def run():
    """Reconcile the three bundled sample documents."""
    return reconcile_paths(DOCUMENTS)


def main():
    _, results = run()
    print_report(results)


if __name__ == "__main__":
    main()
