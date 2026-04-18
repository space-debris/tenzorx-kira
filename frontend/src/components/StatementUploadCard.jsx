import { useState } from 'react';
import { Upload, Loader2, FileText, Sparkles } from 'lucide-react';
import {
  DEFAULT_SAMPLE_CONTENT,
  SAMPLE_STATEMENT_FILES,
  STATEMENT_FILE_ACCEPT,
  inferStatementFileType,
  isBinaryStatementType,
  isSpreadsheetStatementType,
  readStatementFile,
  summarizeCsvContent,
} from '../utils/statementFiles';

export default function StatementUploadCard({
  onSubmit,
  isSubmitting = false,
  title = 'Statement refresh',
  description = 'Upload CSV, PDF, or Excel statements from banks, Paytm, PhonePe, and other UPI providers for monitoring re-score.',
  submitLabel = 'Upload and Re-score',
  useSampleLabel = 'Use sample',
  className = '',
}) {
  const [fileName, setFileName] = useState('statement-refresh.csv');
  const [sourceKind, setSourceKind] = useState('bank');
  const [fileType, setFileType] = useState('text/csv');
  const [mode, setMode] = useState('manual');
  const [content, setContent] = useState(
    DEFAULT_SAMPLE_CONTENT,
  );
  const [readError, setReadError] = useState('');

  const isBinaryPayload = isBinaryStatementType(fileType);
  const isSpreadsheetPayload = isSpreadsheetStatementType(fileType);
  const csvSummary = summarizeCsvContent(isBinaryPayload ? '' : content);

  const handleFileSelection = async (event) => {
    const selected = event.target.files?.[0];
    if (!selected) {
      return;
    }

    const detectedType = inferStatementFileType(selected.name, selected.type);
    setFileName(selected.name);
    setFileType(detectedType);
    setReadError('');
    setMode('file');

    try {
      const nextContent = await readStatementFile(selected, detectedType);
      setContent(nextContent);
    } catch (error) {
      console.error('Failed to read selected statement file', error);
      setReadError('Could not read the selected file. Please try another PDF, CSV, or Excel file.');
      setContent('');
    }
  };

  const enableManualMode = () => {
    setMode('manual');
    setFileType('text/csv');
    if (isBinaryStatementType(fileType)) {
      setFileName('statement-refresh.csv');
    }
    if (!content || isBinaryPayload) {
      setContent(DEFAULT_SAMPLE_CONTENT);
    }
    setReadError('');
  };

  const enableFileMode = () => {
    setMode('file');
    setReadError('');
  };

  const useSampleCsv = () => {
    setMode('manual');
    setFileName('statement-refresh.csv');
    setFileType('text/csv');
    setContent(DEFAULT_SAMPLE_CONTENT);
    setReadError('');
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!content.trim()) {
      setReadError('Statement content is empty. Upload a file or paste statement rows.');
      return;
    }

    onSubmit?.({
      file_name: fileName,
      file_type: fileType,
      source_kind: sourceKind,
      content,
    });
  };

  return (
    <div className={`group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-300 hover:border-primary-200 hover:shadow-lg ${className}`}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-linear-to-r from-primary-500 via-indigo-400 to-sky-400" />
      <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-primary-400/15 blur-2xl" />

      <div className="relative z-10 mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="rounded-xl bg-primary-50 p-2 text-primary-700 ring-1 ring-primary-100">
            <Upload className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{title}</h2>
            <p className="mt-0.5 text-xs font-medium text-slate-600">{description}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={useSampleCsv}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 transition hover:border-primary-200 hover:text-primary-700"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {useSampleLabel}
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-2.5">
        <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            onClick={enableManualMode}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${mode === 'manual' ? 'bg-white text-primary-700 shadow-sm' : 'text-slate-600 hover:text-slate-800'}`}
          >
            Manual CSV
          </button>
          <button
            type="button"
            onClick={enableFileMode}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${mode === 'file' ? 'bg-white text-primary-700 shadow-sm' : 'text-slate-600 hover:text-slate-800'}`}
          >
            Upload File (CSV/PDF/Excel)
          </button>
        </div>

        <div className="grid sm:grid-cols-2 gap-2.5">
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">File name</span>
            <input
              value={fileName}
              onChange={(event) => setFileName(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
              placeholder={isBinaryPayload ? 'statement.pdf / statement.xlsx' : 'statement.csv'}
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Source</span>
            <select
              value={sourceKind}
              onChange={(event) => setSourceKind(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100 bg-white"
            >
              <option value="bank">Bank</option>
              <option value="paytm">Paytm</option>
              <option value="phonepe">PhonePe</option>
              <option value="gpay">Google Pay</option>
              <option value="upi">Other UPI</option>
            </select>
          </label>
        </div>

        {mode === 'file' && (
          <label className="block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Statement file</span>
            <input
              type="file"
              accept={STATEMENT_FILE_ACCEPT}
              onChange={handleFileSelection}
              className="block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-primary-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-primary-700 hover:file:bg-primary-100"
            />
            <div className="text-xs text-slate-500">
              Supported: CSV, PDF, and Excel. PDF and Excel files are encoded and parsed server-side.
            </div>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_STATEMENT_FILES.map((sample) => (
                <a
                  key={sample.href}
                  href={sample.href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 transition hover:border-primary-200 hover:text-primary-700"
                >
                  <FileText className="h-3.5 w-3.5" />
                  {sample.label}
                </a>
              ))}
            </div>
          </label>
        )}

        {readError && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
            {readError}
          </div>
        )}

        <label className={`space-y-1.5 block ${isBinaryPayload ? 'opacity-70' : ''}`}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {isBinaryPayload ? 'Encoded payload' : 'CSV content'}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
              <FileText className="h-3.5 w-3.5" />
              {isBinaryPayload
                ? isSpreadsheetPayload
                  ? 'Excel attached for parsing'
                  : 'PDF attached for parsing'
                : `${csvSummary.rows} row${csvSummary.rows === 1 ? '' : 's'} • ${csvSummary.creditRows} credit • ${csvSummary.debitRows} debit`}
            </span>
          </div>

          {isBinaryPayload ? (
            <div className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-600 leading-snug">
              {isSpreadsheetPayload
                ? 'Excel content is stored in encoded format and sent to the backend extractor. Use total amount / settlement sheets when available for better monthly revenue hints.'
                : 'PDF content is stored in encoded format and sent to the backend parser. You can still change file name/source before upload.'}
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              rows={6}
              className="w-full rounded-xl border border-slate-300 bg-slate-950 px-3 py-2 text-sm font-mono text-slate-100 outline-none transition focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
            />
          )}
        </label>

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-lg disabled:translate-y-0 disabled:bg-slate-300 disabled:shadow-none"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {submitLabel}
        </button>
      </form>
    </div>
  );
}
