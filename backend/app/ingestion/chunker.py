from typing import List, Dict, Any
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:
    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " • ", " - ", ". ", ", ", " "],
            length_function=len,
        )

    def chunk_document(self, parsed_pages: List[Dict[str, Any]], document_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        chunk_index = 0
        
        for page in parsed_pages:
            content = page.get("content", "").strip()
            if not content:
                continue
                
            page_num = page.get("page_number", 1)
            section = page.get("section", f"Page {page_num}")
            
            splits = self.splitter.split_text(content)
            
            for text in splits:
                cleaned_text = text.strip()
                if not cleaned_text:
                    continue
                    
                chunk_id = str(uuid.uuid4())
                chunk = {
                    "id": chunk_id,
                    "chunk_id": chunk_id,
                    "document_id": document_metadata["id"],
                    "user_id": document_metadata["user_id"],
                    "filename": document_metadata["filename"],
                    "chunk_index": chunk_index,
                    "content": cleaned_text,
                    "text": cleaned_text,
                    "page": page_num,
                    "page_number": page_num,
                    "section": section,
                    "chunk_metadata": {
                        "user_id": document_metadata["user_id"],
                        "filename": document_metadata["filename"],
                        "page_number": page_num,
                        "section": section,
                    }
                }
                chunks.append(chunk)
                chunk_index += 1
                
        return chunks

chunker = DocumentChunker()
