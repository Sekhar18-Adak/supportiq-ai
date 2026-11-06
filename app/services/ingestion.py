from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)

from docx import Document as DocxDocument


SUPPORTED = {".pdf", ".txt", ".md", ".docx"}


# -----------------------------------------
# LOAD DOCUMENT
# -----------------------------------------

def load_file(path: Path) -> list[Document]:

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {suffix}")

    try:

        # PDF
        if suffix == ".pdf":
            docs = PyPDFLoader(str(path)).load()

        # TXT / MARKDOWN
        elif suffix in {".txt", ".md"}:
            docs = TextLoader(
                str(path),
                encoding="utf-8"
            ).load()

        # DOCX
        elif suffix == ".docx":

            doc = DocxDocument(str(path))

            content = []

            # Extract paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content.append(paragraph.text)

            # Extract tables
            for table in doc.tables:
                for row in table.rows:

                    row_text = " | ".join(
                        cell.text.strip()
                        for cell in row.cells
                    )

                    if row_text.strip():
                        content.append(row_text)

            text = "\n".join(content)

            docs = [
                Document(
                    page_content=text,
                    metadata={"source": str(path)}
                )
            ]

        else:
            raise ValueError(
                f"Unsupported file type: {suffix}"
            )

        # Ensure consistent source metadata
        for document in docs:
            document.metadata["source"] = str(path)

        if not docs or not any(
            document.page_content.strip()
            for document in docs
        ):
            raise ValueError(
                f"No readable content found in: {path.name}"
            )

        return docs

    except Exception as e:

        raise RuntimeError(
            f"Failed to load {path.name}: {str(e)}"
        ) from e


# -----------------------------------------
# CHUNK DOCUMENTS
# -----------------------------------------

def chunk_documents(
    docs: Iterable[Document]
) -> list[Document]:

    docs = list(docs)

    if not docs:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        add_start_index=True,
    )

    chunks = splitter.split_documents(docs)

    return chunks
