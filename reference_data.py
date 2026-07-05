import re

def check_hs_code(value: str):
    if not value:
        return None, ""
    try:
        import pyhscodes
    except ImportError:
        return None, "pyhscodes not installed"

    digits = re.sub(r"\D", "", value)
    if len(digits) < 6:
        return False, f"HS code '{value}' is too short (need 6 digits)"

    entry = pyhscodes.hscodes.get(hscode=digits[:6])
    if entry is None:
        return False, f"HS code {digits[:6]} not found in HS nomenclature"
    return True, f"HS {digits[:6]}: {entry.description}"


import csv
from pathlib import Path

_PORT_CSV = Path(__file__).with_name("data") / "code-list.csv"
_PORT_INDEX = None


def _norm(name: str) -> str:
    return " ".join(name.upper().split())


def _load_ports() -> dict:
    """name -> (unlocode, "Name, Country", is_seaport). Cached after first call."""
    global _PORT_INDEX
    if _PORT_INDEX is not None:
        return _PORT_INDEX

    index = {}
    if not _PORT_CSV.exists():
        _PORT_INDEX = index
        return index

    with _PORT_CSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            loc = (row.get("Location") or "").strip()
            country = (row.get("Country") or "").strip()
            name = (row.get("NameWoDiacritics") or row.get("Name") or "").strip()
            if not loc or not name:
                continue
            func = row.get("Function") or ""
            is_port = func[:1] == "1"
            code = country + loc
            key = _norm(name)
            existing = index.get(key)
            if existing is None or (is_port and not existing[2]):
                index[key] = (code, f"{name}, {country}", is_port)

    _PORT_INDEX = index
    return index


def check_port(value: str):
    if not value:
        return None, ""
    ports = _load_ports()
    if not ports:
        return None, "UN/LOCODE dataset not found (data/code-list.csv)"

    entry = ports.get(_norm(value))
    if entry is None:
        return False, f"Port '{value}' not found in UN/LOCODE reference"
    code, display, is_port = entry
    kind = "seaport" if is_port else "location - not marked as a seaport"
    return True, f"UN/LOCODE {code} ({display}) - {kind}"

CARRIER_PREFIXES = {
    "MEDU": "MSC (Mediterranean Shipping Company)",
    "MSCU": "MSC (Mediterranean Shipping Company)",
    "MAEU": "Maersk Line",
    "MRKU": "Maersk Line",
    "MSKU": "Maersk Line",
    "HLCU": "Hapag-Lloyd",
    "HLXU": "Hapag-Lloyd",
    "CMAU": "CMA CGM",
    "CGMU": "CMA CGM",
    "COSU": "COSCO Shipping",
    "OOLU": "OOCL",
    "EGLV": "Evergreen Line",
    "EISU": "Evergreen Line",
    "ONEY": "Ocean Network Express (ONE)",
    "YMLU": "Yang Ming",
    "HMMU": "HMM (Hyundai)",
    "APLU": "APL",
    "ZIMU": "ZIM",
}


def check_bl_number(value: str):
    """Recognise the carrier from the B/L number's 4-letter prefix and do a
    light structural sanity check."""
    if not value:
        return None, ""
    v = value.strip().upper()
    m = re.match(r"^([A-Z]{4})", v)
    if not m:
        return False, f"B/L number '{value}' has no 4-letter carrier prefix"
    prefix = m.group(1)
    if prefix in CARRIER_PREFIXES:
        return True, f"{prefix} format valid ({CARRIER_PREFIXES[prefix]})"
    return False, f"Unrecognised carrier prefix '{prefix}'"


def field_note(field: str, value: str):
    """Return (status, note) ground-truth check for a single field value,
    or (None, "") if the field has no knowledge-base check."""
    if field == "hs_code":
        return check_hs_code(value)
    if field == "port_of_discharge":
        return check_port(value)
    if field == "bl_number":
        return check_bl_number(value)
    if field == "container_no":
        from validation import container_check_digit
        ok, reason = container_check_digit(value)
        return ok, f"ISO 6346 check digit {'valid' if ok else 'INVALID'} - {reason}"
    return None, ""


if __name__ == "__main__":
    samples = [
        ("hs_code", "9403.60"),
        ("hs_code", "0000.00"),
        ("port_of_discharge", "BRISBANE"),
        ("port_of_discharge", "ATLANTIS"),
        ("bl_number", "MEDUSG512884170"),
        ("bl_number", "XXXX123"),
        ("container_no", "MEDU7745120"),
    ]
    for f, v in samples:
        status, note = field_note(f, v)
        flag = {True: "OK ", False: "XX ", None: " . "}[status]
        print(f"[{flag}] {f:18} {v:22} -> {note}")
