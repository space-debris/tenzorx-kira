/**
 * KIRA — Image Uploader Component
 *
 * Multi-image upload (3-5 images) with preview and type selection.
 * Each image can be tagged as: interior, exterior, shelf_closeup.
 *
 * Owner: Frontend Lead
 * Phase: 5.2
 *
 * Props:
 *   images (array) — Current uploaded images [{file, preview, type}]
 *   onImagesChange (function) — Callback when images change
 */

import { useState } from 'react';
import { UploadCloud, X, Image as ImageIcon, CheckCircle2, AlertCircle } from 'lucide-react';

export default function ImageUploader({ images = [], onImagesChange }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);

  const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB
  const MAX_FILES = 5;

  const handleFiles = (files) => {
    setError(null);
    const validFiles = [];
    
    if (images.length + files.length > MAX_FILES) {
      setError(`You can only upload a maximum of ${MAX_FILES} images.`);
      return;
    }

    for (const file of files) {
      if (file.size > MAX_FILE_SIZE) {
        setError(`File ${file.name} exceeds the 2MB limit.`);
        continue;
      }
      if (!file.type.match(/image\/(jpeg|png)/i)) {
        setError(`File ${file.name} is not a valid JPEG or PNG image.`);
        continue;
      }
      
      // Auto-assign default type based on sequence broadly
      let defaultType = 'interior';
      if (images.length + validFiles.length === 1) defaultType = 'exterior';
      if (images.length + validFiles.length === 2) defaultType = 'shelf_closeup';

      validFiles.push({
        id: crypto.randomUUID(),
        file,
        preview: URL.createObjectURL(file),
        type: defaultType
      });
    }

    if (validFiles.length > 0) {
      onImagesChange([...images, ...validFiles]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const removeImage = (id) => {
    const filtered = images.filter(img => img.id !== id);
    onImagesChange(filtered);
    
    // Revoke object URL to avoid memory leaks
    const removedImg = images.find(img => img.id === id);
    if (removedImg) URL.revokeObjectURL(removedImg.preview);
  };

  const handleTypeChange = (id, newType) => {
    const updated = images.map(img => img.id === id ? { ...img, type: newType } : img);
    onImagesChange(updated);
  };

  return (
    <div className="bg-white border text-left border-slate-200 rounded-xl p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800">
          <ImageIcon className="text-indigo-600" /> Store Imagery
        </h2>
        <div className={`px-3 py-1 rounded-full text-xs font-bold ${images.length >= 3 && images.length <= 5 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
          {images.length}/5 Uploaded (Min 3)
        </div>
      </div>

      <p className="text-sm text-slate-600 mb-6">
        Provide 3-5 images (Max 2MB each). We require pictures of the storefront exterior, the general interior layout, and a close-up of the stocked shelves to evaluate inventory working capital.
      </p>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg flex items-start gap-2 mb-4 text-sm font-medium">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {images.length < MAX_FILES && (
        <div 
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer mb-6 ${isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-upload').click()}
        >
          <UploadCloud className={`w-12 h-12 mx-auto mb-3 ${isDragging ? 'text-indigo-600' : 'text-slate-400'}`} />
          <p className="font-semibold text-slate-700 mb-1">Drag and drop images here</p>
          <p className="text-sm text-slate-500">or click to browse JPEG/PNG files</p>
          <input 
            type="file" 
            id="file-upload" 
            multiple 
            accept="image/jpeg, image/png" 
            className="hidden" 
            onChange={(e) => handleFiles(Array.from(e.target.files))}
          />
        </div>
      )}

      {images.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {images.map((img) => (
            <div key={img.id} className="relative border border-slate-200 rounded-xl overflow-hidden group shadow-sm bg-slate-50 flex flex-col">
              <button 
                onClick={() => removeImage(img.id)}
                className="absolute top-2 right-2 bg-black/60 text-white p-1.5 rounded-full hover:bg-red-600 transition-colors z-10"
                title="Remove image"
              >
                <X className="w-4 h-4" />
              </button>
              
              <div className="h-40 overflow-hidden bg-slate-200">
                <img src={img.preview} alt="Store preview" className="w-full h-full object-cover transition-transform group-hover:scale-105 duration-300" />
              </div>
              
              <div className="p-3 border-t border-slate-200">
                <label className="block text-xs font-semibold text-slate-500 mb-1">Image Type:</label>
                <select 
                  value={img.type} 
                  onChange={(e) => handleTypeChange(img.id, e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded p-1.5 text-sm font-medium outline-none focus:border-indigo-500"
                >
                  <option value="interior">Interior Overview</option>
                  <option value="exterior">Store Exterior / Facade</option>
                  <option value="shelf_closeup">Shelf Close-up</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
