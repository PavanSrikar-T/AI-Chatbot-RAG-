import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument
import markdown
from bs4 import BeautifulSoup
from typing import Dict, Any, List

class DocumentParser:
    def parse_file(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """
        Parses a file and returns a list of pages/sections with metadata.
        """
        file_type = file_type.lower().strip().lstrip('.')
        if file_type == "pdf":
            return self._parse_pdf(file_path)
        elif file_type == "docx":
            return self._parse_docx(file_path)
        elif file_type == "doc":
            raise ValueError("Legacy .doc format is not supported. Please convert to .docx and try again.")
        elif file_type in ["txt", "md"]:
            return self._parse_text(file_path, file_type)
        else:
            raise ValueError(f"Unsupported file type: {file_type}. Supported types: pdf, docx, txt, md")

    def _parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        pages = []
        has_text = False
        with fitz.open(file_path) as doc:
            if len(doc) == 0:
                raise ValueError("PDF document is empty (0 pages).")
                
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text and text.strip():
                    has_text = True
                pages.append({
                    "page_number": page_num + 1,
                    "content": text.strip() if text else "",
                    "section": f"Page {page_num + 1}"
                })
        
        if not has_text:
            raise ValueError("This PDF does not contain extractable text. OCR is required.")
            
        return pages

    def _parse_docx(self, file_path: str) -> List[Dict[str, Any]]:
        doc = DocxDocument(file_path)
        parts = []
        
        # Extract paragraphs
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)
                
        # Extract tables (vital for resumes and structured docs)
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    parts.append(" | ".join(row_cells))
                    
        full_text = "\n\n".join(parts).strip()
        if not full_text:
            raise ValueError("This DOCX document does not contain extractable text.")
            
        return [{
            "page_number": 1,
            "content": full_text,
            "section": "Document"
        }]

    def _parse_text(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
                text = f.read()
            
        if file_type == "md":
            html = markdown.markdown(text)
            text = "".join(BeautifulSoup(html, "html.parser").stripped_strings)
            
        text = text.strip()
        if not text:
            raise ValueError(f"This {file_type.upper()} file is empty.")
            
        return [{
            "page_number": 1,
            "content": text,
            "section": "Document"
        }]

parser = DocumentParser()
