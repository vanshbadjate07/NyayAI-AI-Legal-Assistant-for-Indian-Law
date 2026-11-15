import { useState } from "react";
import { X, Scale } from "lucide-react";
import { useAuth } from "../lib/auth.jsx";

function GoogleIcon() {
  return <svg width="18" height="18" viewBox="0 0 18 18"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.56 2.7-3.87 2.7-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.81.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.9v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.16.29-1.7V4.97H.9A9 9 0 0 0 0 9c0 1.45.35 2.83.9 4.03l3.05-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .9 4.97l3.05 2.33C4.66 5.17 6.65 3.58 9 3.58z"/></svg>;
}

export default function LoginModal({ open, onClose, reason }) {
  const { loginWithGoogle } = useAuth();
  const [loading, setLoading] = useState(false);
  if (!open) return null;

  async function go() { setLoading(true); await loginWithGoogle(); setLoading(false); onClose(); }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white border border-stone-200 rounded-2xl shadow-modal w-full max-w-sm p-7 text-center animate-fade-up">
        <button onClick={onClose} className="absolute top-4 right-4 text-stone-400 hover:text-stone-700 cursor-pointer"><X size={18} /></button>
        <div className="w-12 h-12 rounded-2xl bg-forest-700 grid place-items-center mx-auto mb-4">
          <Scale size={20} className="text-white" />
        </div>
        <h3 className="font-display text-2xl text-stone-900 mb-2">
          {reason === "upload" ? "Sign in to upload" : "Continue free"}
        </h3>
        <p className="text-sm text-stone-500 mb-6 leading-relaxed">
          {reason === "upload"
            ? "Document uploads require an account to keep your files private."
            : "You've used your 3 free questions. Sign in — still completely free — to keep going."}
        </p>
        <button onClick={go} disabled={loading}
          className="w-full flex items-center justify-center gap-3 bg-white border border-stone-200 rounded-full py-3 text-stone-700 font-semibold text-sm hover:bg-stone-50 hover:border-stone-300 transition-colors disabled:opacity-60 cursor-pointer shadow-card">
          <GoogleIcon /> {loading ? "Signing in..." : "Continue with Google"}
        </button>
        <p className="text-[11px] text-stone-400 mt-4">Demo mode — real Google OAuth coming soon.</p>
      </div>
    </div>
  );
}
