import { useCallback, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, FileUp, Loader2, Upload } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCurrency(value) {
  if (value == null) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

const STATUS_STYLES = {
  uploaded: 'bg-blue-50 text-blue-700 border-blue-200',
  parsing: 'bg-amber-50 text-amber-700 border-amber-200',
  parsed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
};

export default function StatementUploadCard({
  loanId,
  uploads = [],
  onUploadComplete,
  userId,
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleUpload = useCallback(
    async (file) => {
      if (!file || !loanId) return;

      const allowed = ['application/pdf', 'text/csv', 'application/vnd.ms-excel'];
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!allowed.includes(file.type) && !['pdf', 'csv'].includes(ext || '')) {
        setError('Only PDF and CSV files are supported.');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be under 10 MB.');
        return;
      }

      setError(null);
      setIsUploading(true);

      try {
        const formData = new FormData();
        formData.append('file', file);
        if (userId) formData.append('uploaded_by_user_id', userId);

        const response = await fetch(
          `${API_BASE}/api/v1/platform/loans/${loanId}/statements`,
          { method: 'POST', body: formData }
        );

        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || `Upload failed (${response.status})`);
        }

        const result = await response.json();
        onUploadComplete?.(result);
      } catch (err) {
        setError(err.message || 'Upload failed');
      } finally {
        setIsUploading(false);
      }
    },
    [loanId, userId, onUploadComplete]
  );

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleUpload(file);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <FileUp className="w-5 h-5 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
          Statement Upload
        </h2>
      </div>

      {/* Drop Zone */}
      <div
        className={`relative rounded-xl border-2 border-dashed p-6 text-center transition-all cursor-pointer ${
          dragActive
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-200 bg-slate-50 hover:border-indigo-300 hover:bg-slate-100'
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.csv"
          className="hidden"
          onChange={handleFileChange}
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-2 text-indigo-600">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span className="text-sm font-semibold">Uploading & parsing...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-slate-500">
            <Upload className="w-8 h-8" />
            <span className="text-sm font-semibold">
              Drop a bank or UPI statement here
            </span>
            <span className="text-xs text-slate-400">PDF or CSV (max 10 MB)</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Upload History */}
      {uploads.length > 0 && (
        <div className="mt-5">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 mt-5">
            Upload History
          </div>
          <div className="space-y-2">
            {uploads.map((upload) => (
              <div
                key={upload.id}
                className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-4 py-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-800 truncate">
                    {upload.file_name}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                    <span>{formatBytes(upload.file_size_bytes)}</span>
                    <span>{formatDate(upload.created_at)}</span>
                  </div>
                  {upload.transaction_summary && (
                    <div className="flex items-center gap-3 text-xs text-slate-600 mt-1">
                      <span>Credits: {formatCurrency(upload.transaction_summary.total_credits)}</span>
                      <span>Debits: {formatCurrency(upload.transaction_summary.total_debits)}</span>
                      <span>{upload.transaction_summary.period_days}d period</span>
                    </div>
                  )}
                  {upload.parse_error && (
                    <div className="text-xs text-red-600 mt-1">Error: {upload.parse_error}</div>
                  )}
                </div>
                <span
                  className={`px-2 py-1 rounded-full border text-[11px] font-bold uppercase ${
                    STATUS_STYLES[upload.status] || STATUS_STYLES.uploaded
                  }`}
                >
                  {upload.status === 'parsed' && <CheckCircle2 className="w-3 h-3 inline mr-1" />}
                  {upload.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
