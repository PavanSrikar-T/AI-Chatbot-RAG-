import { useState, useRef } from 'react';
import { 
  UploadCloud, 
  Search, 
  Trash2, 
  Loader2, 
  RefreshCw, 
  Layers, 
  AlertCircle, 
  CheckCircle2, 
  X,
  FileText,
  Calendar
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentApi, type Document, type DocumentChunk } from '../api/documents';

export default function KnowledgeBase() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<Document | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentApi.getDocuments,
    refetchInterval: (query) => {
      const docs = query.state.data as Document[] | undefined;
      const hasProcessing = docs?.some((d) => d.status === 'processing');
      return hasProcessing ? 2000 : false;
    },
  });

  const { data: chunks = [], isLoading: isLoadingChunks } = useQuery({
    queryKey: ['document-chunks', selectedDocForChunks?.id],
    queryFn: () => selectedDocForChunks ? documentApi.getDocumentChunks(selectedDocForChunks.id) : Promise.resolve([]),
    enabled: !!selectedDocForChunks,
  });

  const uploadMutation = useMutation({
    mutationFn: documentApi.uploadDocument,
    onSuccess: () => {
      setErrorMessage(null);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
    },
    onError: (err: any) => {
      setErrorMessage(err.message || 'Failed to upload document');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: documentApi.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      if (selectedDocForChunks) {
        setSelectedDocForChunks(null);
      }
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: documentApi.reprocessDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadMutation.mutate(e.target.files[0]);
      e.target.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadMutation.mutate(e.dataTransfer.files[0]);
    }
  };

  const filteredDocs = documents.filter((doc: Document) => 
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.file_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-8 rounded-3xl bg-white border border-slate-200 shadow-card">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/80 mb-2">
            <FileText className="w-3.5 h-3.5" /> Career Digital Twin Knowledge Base
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Resume & Documents</h1>
          <p className="text-slate-500 mt-1 text-sm md:text-base">
            Upload resumes, project reports, and career portfolios to ground AI responses and power your Career Digital Twin.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-xl shadow-sm shadow-blue-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4" />
                <span>Upload Document</span>
              </>
            )}
          </button>
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept=".pdf,.docx,.txt,.md"
            onChange={handleFileChange} 
          />
        </div>
      </div>

      {errorMessage && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl p-4 flex items-center justify-between animate-in slide-in-from-top-2">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-600" />
            <span className="text-xs font-medium">{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Upload Drag & Drop Zone */}
      <div 
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-3xl p-10 text-center transition-all cursor-pointer relative overflow-hidden group ${
          isDragOver
            ? 'border-blue-500 bg-blue-50/80 shadow-md scale-[1.01]'
            : 'border-blue-200 bg-gradient-to-b from-blue-50/40 via-white to-indigo-50/20 hover:border-blue-400 hover:bg-blue-50/50 shadow-card'
        }`}
      >
        <div className="relative z-10 flex flex-col items-center">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mb-4 border border-blue-100 shadow-sm group-hover:scale-105 transition-transform text-blue-600">
            {uploadMutation.isPending ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <UploadCloud className="w-8 h-8" />
            )}
          </div>
          <h3 className="text-lg font-bold text-slate-900 mb-1">
            Drag & drop your document here, or browse files
          </h3>
          <p className="text-xs text-slate-500 mb-4 max-w-md">
            Upload your latest resume (PDF, DOCX) to automatically extract your skills, project ownership, and experience.
          </p>

          <div className="flex items-center gap-2 text-xs">
            <span className="px-3 py-1 bg-white border border-slate-200 rounded-lg font-mono text-slate-600 text-[11px] font-semibold">PDF</span>
            <span className="px-3 py-1 bg-white border border-slate-200 rounded-lg font-mono text-slate-600 text-[11px] font-semibold">DOCX</span>
            <span className="px-3 py-1 bg-white border border-slate-200 rounded-lg font-mono text-slate-600 text-[11px] font-semibold">TXT</span>
            <span className="px-3 py-1 bg-white border border-slate-200 rounded-lg font-mono text-slate-600 text-[11px] font-semibold">Max 15MB</span>
          </div>

          {/* Clean RAG Ingestion Pipeline Stepper */}
          {uploadMutation.isPending && (
            <div className="mt-6 p-4 rounded-2xl bg-white border border-blue-200 shadow-xs w-full max-w-lg space-y-2 animate-in fade-in">
              <div className="flex items-center justify-between text-xs font-semibold text-blue-700">
                <span>RAG Ingestion Pipeline</span>
                <span className="animate-pulse">Processing Vector Embeddings...</span>
              </div>
              <div className="grid grid-cols-5 gap-1.5 text-[10px] text-center font-mono">
                <span className="p-1 rounded bg-blue-100 text-blue-800 font-bold">1. Upload</span>
                <span className="p-1 rounded bg-blue-100 text-blue-800 font-bold">2. Parse</span>
                <span className="p-1 rounded bg-blue-100 text-blue-800 font-bold">3. Chunk</span>
                <span className="p-1 rounded bg-blue-600 text-white font-bold animate-pulse">4. Embed</span>
                <span className="p-1 rounded bg-slate-100 text-slate-500">5. Index</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Document List Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl font-bold text-slate-900">Your Indexed Documents</h2>
            <span className="text-xs bg-blue-50 text-blue-700 font-bold px-2.5 py-0.5 rounded-full border border-blue-200">
              {documents.length} Files
            </span>
          </div>

          {/* Search Documents */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by filename or format..." 
              className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800 placeholder:text-slate-400 shadow-2xs"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-3 bg-white rounded-3xl border border-slate-200">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <span className="text-xs text-slate-500">Loading indexed documents...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDocs.length > 0 ? filteredDocs.map((doc: Document) => (
              <div 
                key={doc.id} 
                className="p-6 rounded-3xl bg-white border border-slate-200 hover:border-blue-300 hover:shadow-card-hover transition-all flex flex-col justify-between space-y-4 group shadow-card"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center font-bold text-xs uppercase border border-blue-100">
                      {doc.file_type || 'PDF'}
                    </div>

                    <div className="flex items-center gap-1">
                      {doc.status === 'error' && (
                        <button 
                          onClick={() => reprocessMutation.mutate(doc.id)} 
                          title="Reprocess Document"
                          disabled={reprocessMutation.isPending}
                          className="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg hover:bg-slate-50 transition-colors"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                      )}
                      <button 
                        onClick={() => {
                          if (confirm(`Are you sure you want to delete "${doc.filename}"?`)) {
                            deleteMutation.mutate(doc.id);
                          }
                        }}
                        title="Delete Document"
                        disabled={deleteMutation.isPending}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <h4 className="font-bold text-slate-900 text-sm mb-1 truncate" title={doc.filename}>
                    {doc.filename}
                  </h4>

                  <div className="flex items-center text-xs text-slate-400 space-x-2 pt-0.5">
                    <span className="uppercase font-semibold text-slate-500">{doc.file_type}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-400" />
                      {new Date(doc.created_at).toLocaleDateString()}
                    </span>
                    {doc.metadata_?.chunk_count !== undefined && (
                      <>
                        <span>•</span>
                        <span className="font-semibold text-slate-600">{doc.metadata_.chunk_count} chunks</span>
                      </>
                    )}
                  </div>

                  {doc.metadata_?.error && (
                    <div className="mt-3 text-xs bg-rose-50 text-rose-700 border border-rose-200 rounded-xl p-2.5 flex items-start gap-1.5 line-clamp-2" title={doc.metadata_.error}>
                      <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                      <span>{doc.metadata_.error}</span>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    {doc.status === 'completed' && (
                      <span className="inline-flex items-center text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">
                        <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" /> Processed & Indexed
                      </span>
                    )}
                    {doc.status === 'processing' && (
                      <span className="inline-flex items-center text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">
                        <Loader2 className="w-3 h-3 mr-1 animate-spin text-amber-600" /> Chunking in RAG...
                      </span>
                    )}
                    {doc.status === 'error' && (
                      <span className="inline-flex items-center text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-0.5 rounded-full text-xs font-semibold">
                        <AlertCircle className="w-3 h-3 mr-1 text-rose-600" /> Error
                      </span>
                    )}
                  </div>
                  
                  {doc.status === 'completed' && (
                    <button 
                      onClick={() => setSelectedDocForChunks(doc)}
                      className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 hover:underline"
                    >
                      <Layers className="w-3.5 h-3.5" /> View Chunks
                    </button>
                  )}
                </div>
              </div>
            )) : (
              <div className="col-span-3 text-center py-16 px-6 bg-white rounded-3xl border border-dashed border-slate-200 space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                  <FileText className="w-6 h-6" />
                </div>
                <h4 className="text-base font-bold text-slate-800">
                  {searchTerm ? 'No documents match your search' : 'No documents indexed yet'}
                </h4>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  {searchTerm ? 'Try a different filename or keyword.' : 'Upload your resume or project documentation above to activate real-time RAG and job matching.'}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chunk Viewer Light Modal */}
      {selectedDocForChunks && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-6 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">{selectedDocForChunks.filename}</h3>
                  <p className="text-xs text-slate-400">Indexed Document Chunks in Vector Database (Qdrant)</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedDocForChunks(null)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {isLoadingChunks ? (
                <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>
              ) : chunks.length > 0 ? (
                chunks.map((chunk: DocumentChunk) => (
                  <div key={chunk.id} className="p-4 rounded-2xl border border-slate-200 bg-slate-50/60 hover:border-blue-300 transition-colors space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-md">
                        Chunk #{chunk.chunk_index + 1}
                      </span>
                      {chunk.page_number && (
                        <span className="text-xs text-slate-500 font-medium">
                          Page {chunk.page_number}
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-mono whitespace-pre-wrap leading-relaxed bg-white p-3.5 rounded-xl border border-slate-200 text-slate-800">
                      {chunk.content}
                    </p>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-slate-400 text-xs">
                  No chunks indexed for this document.
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-100 flex justify-end">
              <button 
                onClick={() => setSelectedDocForChunks(null)}
                className="px-5 py-2.5 bg-slate-100 text-slate-700 font-semibold rounded-xl hover:bg-slate-200 transition-colors text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
