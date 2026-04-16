import { useState } from 'react';
import { Upload, Loader2 } from 'lucide-react';

export default function StatementUploadCard({ onSubmit, isSubmitting = false }) {
  const [fileName, setFileName] = useState('statement-refresh.csv');
  const [sourceKind, setSourceKind] = useState('bank');
  const [content, setContent] = useState(
    'date,description,amount,type\n2026-04-01,Supplier Traders,22000,debit\n2026-04-02,Customer UPI,48000,credit\n',
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.({
      file_name: fileName,
      file_type: 'text/csv',
      source_kind: sourceKind,
      content,
    });
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Upload className="w-4 h-4 text-primary-600" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Statement Refresh</h2>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid sm:grid-cols-2 gap-3">
          <input
            value={fileName}
            onChange={(event) => setFileName(event.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary-500"
            placeholder="statement.csv"
          />
          <select
            value={sourceKind}
            onChange={(event) => setSourceKind(event.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary-500 bg-white"
          >
            <option value="bank">Bank</option>
            <option value="upi">UPI</option>
          </select>
        </div>
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={6}
          className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm font-mono outline-none focus:border-primary-500"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-300 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          Upload and Re-score
        </button>
      </form>
    </div>
  );
}
