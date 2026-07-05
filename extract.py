from dotenv import load_dotenv
load_dotenv()
import os
import json
from pathlib import Path

TARGET_FIELDS = [
    "bl_number", "container_no", "seal_no", "consignee",
    "vessel_name", "voyage_no", "port_of_discharge", "gross_weight",
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
- container_no is a shipping CONTAINER number, always formatted as EXACTLY 4 uppercase letters followed by 7 digits (ISO 6346), e.g. "MEDU7745120". Extract it from EVERY document that shows a container number (Bill of Lading, Shipping Instruction, and VGM Certificate all carry one). Return the code only, with no surrounding words.
- bl_number is the Bill of Lading / document number, usually labelled "B/L No.", "Bill of Lading No.", "Booking No.", or "Document No." (e.g. "MEDUSG512884170"). It is NOT a container number: a code in the 4-letters-then-7-digits container format must go in container_no, NEVER in bl_number. If the document does not clearly show its OWN Bill of Lading number, set bl_number to null - do not borrow the container number to fill it. Shipping Instructions and VGM Certificates usually have no Bill of Lading number.
- For seal_no, return the seal code exactly as printed, with no surrounding words.
- vessel_name and voyage_no are TWO SEPARATE fields. Never combine them.
- vessel_name is the ship's name only (e.g. "MSC POH LIN"). Exclude any voyage number, call sign, or IMO number.
- voyage_no is the voyage number only: a short alphanumeric sailing code, usually labelled "Voyage No.", "Voy", or similar (e.g. "FE842A"). Exclude the vessel name. If the document shows only a VCN (Vessel Call Number) such as "SIN2018FE842A" instead of a plain voyage number, the voyage number is the recognisable voyage code embedded in it (here "FE842A") - extract ONLY that code, dropping the port/year prefix (e.g. "SIN2018").

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


CACHE_PATH = "samples/extracted_live.json"


def is_live() -> bool:
    if os.environ.get("BL_RECONCILER_REPLAY"):
        return False
    return bool(os.environ.get("GROQ_API_KEY"))


def extract_fields(pdf_path: str, doc_name: str, replay: bool = False) -> dict:

    if not replay and is_live():
        text = read_pdf_text(pdf_path)
        prompt = build_prompt(text)
        raw = call_llm(prompt)
        return parse_json_reply(raw)

    cache = Path(CACHE_PATH)
    if not cache.exists():
        raise RuntimeError(
            f"No cached extraction at {CACHE_PATH}. Run once with GROQ_API_KEY set "
            "to produce a real extraction before using replay mode."
        )
    print(f"[replay] reusing last real extraction for {doc_name!r}")
    return json.loads(cache.read_text()).get(doc_name, {})


if __name__ == "__main__":
    fields = extract_fields("samples/Sample_Bill_of_Lading.pdf", "Bill of Lading")
    print(json.dumps(fields, indent=2))
