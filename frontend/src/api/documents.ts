import { fetchApi } from './client';

export interface Document {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  status: string;
  created_at: string;
  metadata_?: {
    chunk_count?: number;
    pages_count?: number;
    error?: string;
    note?: string;
  };
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  page_number?: number;
  section?: string;
  chunk_metadata?: Record<string, any>;
}

export const documentApi = {
  getDocuments: (): Promise<Document[]> => {
    return fetchApi('/documents/');
  },

  getDocument: (id: string): Promise<Document> => {
    return fetchApi(`/documents/${id}`);
  },

  getDocumentChunks: (id: string): Promise<DocumentChunk[]> => {
    return fetchApi(`/documents/${id}/chunks`);
  },
  
  uploadDocument: (file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    
    return fetchApi('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },

  deleteDocument: (id: string): Promise<{ message: string; id: string }> => {
    return fetchApi(`/documents/${id}`, {
      method: 'DELETE',
    });
  },

  reprocessDocument: (id: string): Promise<{ message: string; id: string }> => {
    return fetchApi(`/documents/${id}/reprocess`, {
      method: 'POST',
    });
  },
};
