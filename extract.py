from dotenv import load_dotenv
load_dotenv()
import os
import json
from pathlib import Path

# The exact fields we want out of every document.
TARGET_FIELDS = [
    "bl_number", "container_no", "seal_no", "consignee",
    "vessel_voyage", "port_of_discharge", "gross_weight",
    "hs_code", "package_count", "vgm_kg",
]

def read_pdf_text(pdf_path: str) -> str:
    """Return all text found in the PDF as one big string."""
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def build_prompt(document_text: str) -> str:
    fields_list = ", ".join(TARGET_FIELDS)
    return f"""You are a precise data-extraction assistant for shipping documents.

Extract the following fields from the document text below:
{fields_list}

Rules:
- Return ONLY a valid JSON object. No explanations, no markdown, no ``` fences.
- Use the exact field names listed above as the JSON keys.
- If a field is not present in the document, set its value to null.
- Preserve the meaning of each value faithfully, but format it consistently using the rules below.
- Output each value as a SINGLE LINE. Replace any line breaks inside a value with a single space.
- For location or port fields, if a code appears in parentheses (e.g. "BRISBANE (AUBNE)"), keep only the name and drop the parenthetical code.
- Do not add punctuation or separators that are not needed. For combined fields like vessel and voyage, separate the two parts with a single space, not slashes.
- Keep numbers, dates, and codes (like HS codes) exactly as written.
- For consignee, return the FULL consignee block on one line: the company / legal name followed by its complete postal address (street, unit, city, state, postal code, country). Do not shorten or drop the address - address differences between documents are meaningful and must be preserved. Exclude only phone, email, and contact person name.
- For package_count, return ONLY the integer number of packages as digits (e.g. "430"). Do not include unit words like "CARTONS" or "PALLETS".
- For container_no and seal_no, return the code exactly as printed, with no surrounding words.
- For vessel_voyage, return ONLY the vessel name followed by the voyage number, separated by a single space. Exclude terminal names, call signs, VCN, or other codes.

Document text:
\"\"\"
{document_text}
\"\"\"
"""

def call_llm(prompt: str) -> str:

    from groq import Groq
    client = Groq()  # reads GROQ_API_KEY from the environment
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def parse_json_reply(raw_reply: str) -> dict:

    cleaned = raw_reply.strip()
    if cleaned.startswith("```"):
        # remove ```json ... ``` fences if present
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    return json.loads(cleaned)


def extract_fields(pdf_path: str, doc_name: str) -> dict:
    if os.environ.get("GROQ_API_KEY"):
        text = read_pdf_text(pdf_path)
        prompt = build_prompt(text)          # your code
        raw = call_llm(prompt)               # your code
        return parse_json_reply(raw)         # your code
    else:
        print(f"[mock mode] no API key set - loading mocked fields for {doc_name!r}")
        all_mock = json.loads(Path("samples/extracted.json").read_text())
        return all_mock.get(doc_name, {})


if __name__ == "__main__":
    # Quick test. With no API key this prints the mocked B/L fields.
    fields = extract_fields("samples/Sample_Bill_of_Lading.pdf", "Bill of Lading")
    print(json.dumps(fields, indent=2))
