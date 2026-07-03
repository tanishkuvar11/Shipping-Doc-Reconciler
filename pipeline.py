import json
from pathlib import Path

from extract import extract_fields
from reconcile import reconcile, print_report

DOCUMENTS = {
    "Bill of Lading": "samples/Sample_Bill_of_Lading.pdf",
    "Shipping Instruction": "samples/Sample_Shipping_Instruction.pdf",
    "VGM Certificate": "samples/Sample_VGM_Certificate.pdf",
}


def main():
    docs = {}
    for doc_name, pdf_path in DOCUMENTS.items():
        docs[doc_name] = extract_fields(pdf_path, doc_name)

    Path("samples/extracted_live.json").write_text(json.dumps(docs, indent=2))

    results = reconcile(docs)
    print_report(results)


if __name__ == "__main__":
    main()
