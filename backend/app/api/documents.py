from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import shutil
import os
import uuid
import traceback

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentInDBBase, DocumentChunkSchema
from app.ingestion.parser import parser
from app.ingestion.chunker import chunker
from app.rag.embedder import embedder
from app.core.vector_db import qdrant, delete_document_vectors
from qdrant_client.http.models import PointStruct

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def process_document_background(
    document_id: str,
    file_path: str,
    file_type: str,
    user_id: int,
    filename: str
):
    """
    Background worker that parses, chunks, embeds, and indexes a document.
    """
    from app.core.db import async_session_maker
    from fastapi.concurrency import run_in_threadpool
    
    async with async_session_maker() as db:
        try:
            # 1. Parse Document
            parsed_pages = await run_in_threadpool(parser.parse_file, file_path, file_type)
            extracted_text = "\n\n".join([p["content"] for p in parsed_pages if p.get("content")]).strip()
            
            # 2. Chunk Document
            doc_metadata = {"id": document_id, "user_id": user_id, "filename": filename}
            chunks = await run_in_threadpool(chunker.chunk_document, parsed_pages, doc_metadata)
            
            if not chunks:
                # Document has no text content
                result = await db.execute(select(Document).filter(Document.id == document_id))
                doc = result.scalars().first()
                if doc:
                    doc.content = extracted_text[:20000] if extracted_text else ""
                    doc.status = "completed"
                    doc.metadata_ = {
                        "chunk_count": 0,
                        "pages_count": len(parsed_pages),
                        "note": "Document contains no extractable text."
                    }
                    await db.commit()
                return

            # 3. Embed Chunks
            texts_to_embed = [c["content"] for c in chunks]
            embeddings = await run_in_threadpool(embedder.embed_texts, texts_to_embed)
            
            # 4. Insert DocumentChunks into Database
            for c in chunks:
                db_chunk = DocumentChunk(
                    id=c["id"],
                    document_id=c["document_id"],
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    page_number=c["page_number"],
                    section=c["section"],
                    chunk_metadata=c["chunk_metadata"]
                )
                db.add(db_chunk)
            
            # 5. Insert Points into Qdrant Vector Store
            points = []
            for i, c in enumerate(chunks):
                points.append(PointStruct(
                    id=c["id"],
                    vector=embeddings[i],
                    payload={
                        "chunk_id": c["id"],
                        "document_id": c["document_id"],
                        "user_id": user_id,
                        "content": c["content"],
                        "text": c["content"],
                        "page": c["page_number"],
                        "page_number": c["page_number"],
                        "section": c["section"],
                        "filename": filename
                    }
                ))
                
            await run_in_threadpool(
                qdrant.upsert,
                collection_name="careermind_documents",
                points=points
            )
            
            # 6. Update Document Status to Completed
            result = await db.execute(select(Document).filter(Document.id == document_id))
            doc = result.scalars().first()
            if doc:
                doc.content = extracted_text[:50000] if extracted_text else ""
                doc.status = "completed"
                doc.metadata_ = {
                    "chunk_count": len(chunks),
                    "pages_count": len(parsed_pages)
                }
                await db.commit()

        except Exception as e:
            print(f"[Document Processing Error] Failed to process document {document_id}: {e}")
            traceback.print_exc()
            try:
                result = await db.execute(select(Document).filter(Document.id == document_id))
                doc = result.scalars().first()
                if doc:
                    doc.status = "error"
                    doc.metadata_ = {"error": str(e)}
                    await db.commit()
            except Exception:
                pass


@router.post(
    "/upload",
    response_model=DocumentInDBBase,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document",
    description="Upload a PDF, DOCX, TXT, or MD document for background parsing, chunking, and embedding."
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")
        
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Supported: pdf, docx, txt, md")
        
    document_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.{file_ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create DB entry
    db_doc = Document(
        id=document_id,
        user_id=current_user.id,
        title=file.filename,
        filename=file.filename,
        file_type=file_ext,
        content="",
        status="processing",
        metadata_={"chunk_count": 0}
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)
    
    # Process in background
    background_tasks.add_task(
        process_document_background,
        document_id=document_id,
        file_path=file_path,
        file_type=file_ext,
        user_id=current_user.id,
        filename=file.filename
    )
    
    return db_doc


@router.get(
    "/",
    response_model=List[DocumentInDBBase],
    summary="List all documents",
    description="Retrieve all documents uploaded by the current authenticated user, ordered newest first."
)
async def get_documents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    return documents


@router.get(
    "/{document_id}",
    response_model=DocumentInDBBase,
    summary="Get document details",
    description="Retrieve metadata and processing status for a single document."
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get(
    "/{document_id}/chunks",
    response_model=List[DocumentChunkSchema],
    summary="Get document chunks",
    description="Retrieve all indexed chunks and metadata for a specific document."
)
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    chunks_result = await db.execute(
        select(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return chunks_result.scalars().all()


@router.delete(
    "/{document_id}",
    summary="Delete a document",
    description="Deletes a document from the database, purges associated vectors from Qdrant, and cleans up uploaded files."
)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # 1. Remove vectors from Qdrant
    delete_document_vectors(document_id)
    
    # 2. Delete local uploaded file if present
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.{doc.file_type}")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: could not delete local file {file_path}: {e}")
            
    # 3. Delete from DB (cascades to chunks)
    await db.delete(doc)
    await db.commit()
    
    return {"message": "Document deleted successfully", "id": document_id}


@router.post(
    "/{document_id}/reprocess",
    summary="Reprocess a document",
    description="Re-runs parsing, chunking, and embedding for a previously uploaded document."
)
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}.{doc.file_type}")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Original source file not found on disk")
        
    # Clear old vectors & chunks
    delete_document_vectors(document_id)
    old_chunks = await db.execute(select(DocumentChunk).filter(DocumentChunk.document_id == document_id))
    for c in old_chunks.scalars().all():
        await db.delete(c)
        
    doc.status = "processing"
    await db.commit()
    
    background_tasks.add_task(
        process_document_background,
        document_id=document_id,
        file_path=file_path,
        file_type=doc.file_type,
        user_id=current_user.id,
        filename=doc.filename
    )
    
    return {"message": "Document reprocessing started", "id": document_id}
