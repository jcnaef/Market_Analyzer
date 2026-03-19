"""Shared text extraction from PDF and DOCX files."""


def extract_text_from_file(tmp_path: str, ext: str) -> str:
    """Extract raw text from a PDF or DOCX file on disk.

    Args:
        tmp_path: Path to the temporary file.
        ext: File extension, either "pdf" or "docx".

    Returns:
        The extracted text as a string.

    Raises:
        ValueError: If the extension is not supported or text extraction fails.
    """
    if ext == "pdf":
        import pdfplumber

        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    if ext == "docx":
        from docx import Document

        doc = Document(tmp_path)
        return "\n".join(p.text for p in doc.paragraphs)

    raise ValueError(f"Unsupported file type: {ext}")
