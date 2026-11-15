import { useRef, useState } from "react";
import { X, UploadCloud, File } from "lucide-react";

export default function UploadModal({ open, onClose, onUpload, loading }) {
  const [file, setFile] = useState(null);
  const ref = useRef(null);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white border border-stone-200 rounded-2xl shadow-modal w-full max-w-md p-6 animate-fade-up">
        <button onClick={onClose} className="absolute top-4 right-4 text-stone-400 hover:text-stone-700 cursor-pointer"><X size={18} /></button>
        <h3 className="font-display text-2xl text-stone-900 mb-1">Upload a document</h3>
        <p className="text-sm text-stone-500 mb-5">Photo or PDF of a notice, agreement, or letter — English, Hindi, Marathi.</p>
        <label htmlFor="upInput"
          className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-stone-300 rounded-xl py-10 cursor-pointer hover:border-forest-400 hover:bg-forest-50 transition-all">
          {file
            ? <><File size={24} className="text-forest-600" /><span className="text-sm text-stone-700 font-medium px-4 text-center break-all">{file.name}</span></>
            : <><UploadCloud size={24} className="text-stone-400" /><span className="text-sm text-stone-400">Tap to choose file</span></>}
        </label>
        <input id="upInput" ref={ref} type="file" accept="image/png,image/jpeg,image/webp,.pdf" className="hidden"
          onChange={e => setFile(e.target.files?.[0] || null)} />
        <button onClick={() => file && !loading && onUpload(file)} disabled={!file || loading}
          className="w-full mt-4 py-3 rounded-full bg-forest-700 text-white font-semibold text-sm hover:bg-forest-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer">
          {loading ? "Analyzing..." : "Upload & Analyze"}
        </button>
      </div>
    </div>
  );
}
