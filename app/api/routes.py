import logging
import secrets
from pathlib import Path
from uuid import uuid4
from time import perf_counter
from app.services.analytics import get_complete_analytics
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Header,
)
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.rag.workflow import ask
from app.rag.vectorstore import add_documents
from app.services.ingestion import (
    load_file,
    chunk_documents,
    SUPPORTED,
)
from app.services.audit import write_audit


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

settings = get_settings()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# --------------------------------------------------
# DOCUMENTS LIST API
# --------------------------------------------------

@router.get("/documents")
def list_documents():

    supported = {".pdf", ".txt", ".md", ".docx"}

    locations = [
        ("Uploaded", Path(settings.upload_dir)),
        ("Sample KB", Path(settings.sample_kb_dir)),
    ]

    documents = []

    for label, folder in locations:

        if not folder.exists() or not folder.is_dir():
            continue

        for path in folder.iterdir():

            if not path.is_file() or path.suffix.lower() not in supported:
                continue

            try:
                stat = path.stat()

                documents.append({
                    "name": path.name,
                    "extension": path.suffix.lower(),
                    "location": label,
                    "path_label": f"{label} folder",
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc
                    ).isoformat(),
                })

            except OSError:
                continue

    documents.sort(
        key=lambda item: item["modified_at"],
        reverse=True
    )

    uploaded_count = sum(
        item["location"] == "Uploaded"
        for item in documents
    )

    sample_count = sum(
        item["location"] == "Sample KB"
        for item in documents
    )

    return {
        "total": len(documents),
        "uploaded_count": uploaded_count,
        "sample_count": sample_count,
        "documents": documents,
    }

# --------------------------------------------------
# ANALYTICS API
# --------------------------------------------------

@router.get("/analytics")
def analytics(days: int = 7):

    try:

        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="Days must be between 1 and 365"
            )

        data = get_complete_analytics(days)

        return {
            "status": "success",
            "period_days": days,
            "data": data
        }

    except HTTPException:
        raise

    except Exception:

        logger.exception("Analytics API failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to fetch analytics data"
        )
        
# --------------------------------------------------
# REQUEST SCHEMA
# --------------------------------------------------

class ChatRequest(BaseModel):

    question: str = Field(
        min_length=2,
        max_length=3000
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@router.get("/health")
def health():

    return {
        "status": "ok",
        "service": settings.app_name
    }


# --------------------------------------------------
# CHAT API
# --------------------------------------------------

@router.post("/chat")
def chat(payload: ChatRequest):

    start_time = perf_counter()

    try:

        # Execute Agentic RAG workflow
        result = ask(payload.question)

        # Get execution metrics
        response_time_ms = result.get(
            "response_time_ms",
            (perf_counter() - start_time) * 1000
        )

        retry_count = result.get("retry_count", 0)

        # Save successful request in audit database
        write_audit(
            question=payload.question,
            source_used=result.get("source_used", "unknown"),
            trace=result.get("trace", []),
            status="success",
            response_time_ms=response_time_ms,
            retry_count=retry_count
        )

        return {
            "answer": result["answer"],

            "source_used": result["source_used"],

            "trace": result.get("trace", []),

            "citations": result.get("citations", []),

            "rewritten_query": result.get(
                "current_query",
                payload.question
            ),

            "response_time_ms": response_time_ms,

            "retry_count": retry_count
        }

    except Exception:

        response_time_ms = (
            perf_counter() - start_time
        ) * 1000

        logger.exception("Chat API failed")

        # Log failed request
        try:

            write_audit(
                question=payload.question,
                source_used="error",
                trace=["Chat request failed"],
                status="failed",
                response_time_ms=response_time_ms,
                retry_count=0
            )

        except Exception:

            logger.exception("Failed to save error audit log")

        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your question."
        )

# --------------------------------------------------
# DOCUMENT INGESTION API
# --------------------------------------------------

@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    x_admin_key: str = Header(default="")
):

    # ----------------------------------------------
    # ADMIN AUTHENTICATION
    # ----------------------------------------------

    if not settings.admin_api_key or not secrets.compare_digest(
        x_admin_key,
        settings.admin_api_key
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid admin key"
        )

    # ----------------------------------------------
    # FILE VALIDATION
    # ----------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    original_filename = file.filename.replace("\\", "/").split("/")[-1]

    suffix = Path(original_filename).suffix.lower()

    if suffix not in SUPPORTED:

        raise HTTPException(
            status_code=400,
            detail=f"Supported formats: {', '.join(sorted(SUPPORTED))}"
        )

    # ----------------------------------------------
    # READ FILE WITH SIZE LIMIT
    # ----------------------------------------------

    try:

        content = await file.read(MAX_FILE_SIZE + 1)

        if not content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        if len(content) > MAX_FILE_SIZE:

            raise HTTPException(
                status_code=413,
                detail="File size exceeds the 10 MB limit"
            )

        # ------------------------------------------
        # SAVE FILE
        # ------------------------------------------

        upload_dir = Path(settings.upload_dir)

        upload_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # Generate unique filename
        unique_filename = f"{uuid4().hex}{suffix}"

        dest = upload_dir / unique_filename

        dest.write_bytes(content)

        # ------------------------------------------
        # LOAD DOCUMENT
        # ------------------------------------------

        docs = load_file(dest)

        if not docs:

            raise HTTPException(
                status_code=400,
                detail="No readable content found"
            )

        # ------------------------------------------
        # CHUNK DOCUMENTS
        # ------------------------------------------

        chunks = chunk_documents(docs)

        if not chunks:

            raise HTTPException(
                status_code=400,
                detail="No document chunks generated"
            )

        # ------------------------------------------
        # INSERT INTO PINECONE
        # ------------------------------------------

        ids = add_documents(chunks)

        logger.info(
            "Document indexed successfully: %s, chunks: %s",
            original_filename,
            len(chunks)
        )

        # ------------------------------------------
        # RESPONSE
        # ------------------------------------------

        return {
            "message": "Document indexed successfully",

            "file": original_filename,

            "chunks": len(chunks),

            "vectors_created": len(ids),

            "namespace": settings.pinecone_namespace,

            "ids_created": ids
        }

    except HTTPException:
        raise

    except Exception:

        logger.exception(
            "Document ingestion failed: %s",
            original_filename
        )

        # Remove partially processed upload
        if "dest" in locals() and dest.exists():
            dest.unlink()

        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed. Please try again."
        )

    finally:

        await file.close()
