import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates

try:
    from groq import RateLimitError
except Exception:  # groq not installed / older SDK
    RateLimitError = None

from extract import TARGET_FIELDS, is_live
from pipeline import DOCUMENTS, reconcile_paths

app = FastAPI(title="B/L Reconciler")
templates = Jinja2Templates(directory="templates")

# The document slots the UI offers, in order.
SLOTS = ["Bill of Lading", "Shipping Instruction", "VGM Certificate"]


def _render(request: Request, docs, results, error=None):
    mismatches = sum(1 for r in results if r["status"] == "MISMATCH")
    errors = sum(1 for r in results if r.get("valid") is False)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "doc_names": list(docs.keys()),
            "docs": docs,
            "results": results,
            "fields": TARGET_FIELDS,
            "mismatches": mismatches,
            "errors": errors,
            "total": len(results),
            "mode": "LIVE (Groq)" if is_live() else "REPLAY (cached AI extraction)",
            "slots": SLOTS,
            "has_results": bool(results),
            "error": error,
        },
    )


def _extraction_error(exc: Exception) -> str:
    if RateLimitError is not None and isinstance(exc, RateLimitError):
        return ("Groq's free-tier daily token limit has been reached, so live extraction "
                "from your uploads is paused until the quota resets. "
                "In the meantime, click \"Use sample documents\" to see a full "
                "reconciliation from the last real extraction.")
    return f"Extraction failed: {exc}"


@app.get("/", response_class=HTMLResponse)
def index(request: Request, sample: int = 0):
    if sample:
        # Sample button always replays the cached real extraction, so it works
        # even when the live API is rate-limited (and never burns tokens).
        try:
            docs, results = reconcile_paths(DOCUMENTS, replay=True)
        except Exception as exc:
            return _render(request, {}, [], error=_extraction_error(exc))
        return _render(request, docs, results)
    return _render(request, {}, [])


@app.post("/reconcile", response_class=HTMLResponse)
async def reconcile_uploads(
    request: Request,
    bl: UploadFile = File(None),
    si: UploadFile = File(None),
    vgm: UploadFile = File(None),
):
    uploaded = {"Bill of Lading": bl, "Shipping Instruction": si, "VGM Certificate": vgm}

    tmpdir = Path(tempfile.mkdtemp(prefix="bl_reconciler_"))
    documents = {}
    try:
        for label, upload in uploaded.items():
            if upload is not None and upload.filename:
                dest = tmpdir / upload.filename
                with dest.open("wb") as fh:
                    shutil.copyfileobj(upload.file, fh)
                documents[label] = str(dest)

        if not documents:
            # Nothing uploaded — just show the empty landing page again.
            return _render(request, {}, [],
                           error="Please choose at least one PDF before reconciling.")

        try:
            docs, results = reconcile_paths(documents, save=False)
        except Exception as exc:
            return _render(request, {}, [], error=_extraction_error(exc))
        return _render(request, docs, results)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
