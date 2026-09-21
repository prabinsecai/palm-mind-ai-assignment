from io import BytesIO
from pypdf import PdfReader
from app.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError

def extract_text(filename: str, content_type: str, data: bytes) -> str:
    suffix=filename.lower().rsplit(".",1)[-1] if "." in filename else ""
    if suffix == "txt" or content_type == "text/plain":
        text=data.decode("utf-8", errors="replace")
    elif suffix == "pdf" or content_type == "application/pdf":
        reader=PdfReader(BytesIO(data))
        text="\n\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        raise UnsupportedFileTypeError("Only PDF and TXT files are supported")
    text=text.strip()
    if not text: raise EmptyDocumentError("The uploaded document contains no extractable text")
    return text
