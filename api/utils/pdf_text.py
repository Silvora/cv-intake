from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from utils.log import log

try:
    from langchain_community.document_loaders import PDFPlumberLoader
    HAS_PDFPLUMBER_LOADER = True
except ModuleNotFoundError:
    PDFPlumberLoader = None
    HAS_PDFPLUMBER_LOADER = False


def _join_text(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip()).strip()


def extract_pdf_text(file_path: str | Path) -> tuple[str, str]:
    path = Path(file_path)
    log.info("Start extracting PDF text: %s", path)

    if HAS_PDFPLUMBER_LOADER and PDFPlumberLoader is not None:
        try:
            # Keep this path first to stay aligned with the workflow stack.
            loader = PDFPlumberLoader(str(path))
            docs = loader.load()
            merged_text = _join_text(
                [
                    getattr(doc, "page_content", "")
                    for doc in docs
                ]
            )
            log.info(
                "PDFPlumberLoader extract finished: %s, text_length=%s",
                path,
                len(merged_text),
            )
            if merged_text:
                return merged_text, "langchain_pdfplumber_loader"
        except Exception as exc:
            log.exception("PDFPlumberLoader extract failed for %s: %s", path, exc)
    else:
        log.info("PDFPlumberLoader unavailable, skip workflow loader: %s", path)

    text_parts: list[str] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())
    except Exception as exc:
        log.exception("pdfplumber extract failed for %s: %s", path, exc)
        text_parts = []

    merged_text = _join_text(text_parts)
    log.info(
        "pdfplumber extract finished: %s, text_length=%s",
        path,
        len(merged_text),
    )
    if merged_text:
        return merged_text, "pdfplumber"

    text_parts = []
    try:
        # pypdf stays as the weaker fallback for cases where plumber yields nothing.
        reader = PdfReader(str(path))
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text.strip())
    except Exception as exc:
        log.exception("pypdf extract failed for %s: %s", path, exc)
        raise

    merged_text = _join_text(text_parts)
    log.info(
        "pypdf extract finished: %s, text_length=%s",
        path,
        len(merged_text),
    )
    return merged_text, "pypdf"
