import { Scale, Languages, ShieldCheck, Github } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-ink-950 text-parchment-100 border-t border-parchment-100/10">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 py-16 grid sm:grid-cols-2 lg:grid-cols-4 gap-10">
        <div className="lg:col-span-1">
          <div className="flex items-center gap-2 mb-4">
            <span className="relative w-7 h-7 grid place-items-center">
              <span className="absolute inset-0 rounded-full seal-ring" />
              <Scale size={14} className="text-brass-300" />
            </span>
            <span className="font-display text-lg">NyayAI</span>
          </div>
          <p className="text-sm text-parchment-300/60 leading-relaxed max-w-xs mb-4">
            Free legal information for Indian citizens — grounded in actual
            law, not guesses.
          </p>
          <div className="flex items-center gap-3 text-parchment-300/40">
            <Languages size={15} />
            <span className="text-xs">English · Hindi · Marathi</span>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold mb-4 text-brass-400">Coverage</h4>
          <ul className="text-sm space-y-2.5 text-parchment-300/70">
            <li>Right to Information</li>
            <li>Tenancy &amp; Rent</li>
            <li>Consumer Protection</li>
            <li>Family &amp; Marriage</li>
            <li>Criminal Law (BNS/BNSS)</li>
          </ul>
        </div>

        <div>
          <h4 className="text-sm font-semibold mb-4 text-brass-400">How It's Built</h4>
          <ul className="text-sm space-y-2.5 text-parchment-300/70">
            <li>Self-hosted, open models</li>
            <li>Retrieval-grounded answers</li>
            <li>Section-level citations</li>
            <li>No data sold to third parties</li>
          </ul>
        </div>

        <div>
          <h4 className="text-sm font-semibold mb-4 text-brass-400">Important</h4>
          <p className="text-sm text-parchment-300/70 leading-relaxed mb-4">
            NyayAI provides legal information, not legal advice. For
            representation, consult a licensed advocate.
          </p>
          <div className="flex items-center gap-2 text-xs text-jade-300/80">
            <ShieldCheck size={14} />
            <span>Grounded in cited law</span>
          </div>
        </div>
      </div>
      <div className="border-t border-parchment-100/10 py-5">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-parchment-300/40">
          <span>© {new Date().getFullYear()} NyayAI. Built for everyday justice.</span>
          <span className="flex items-center gap-1.5">
            <Github size={13} /> Open-source RAG pipeline
          </span>
        </div>
      </div>
    </footer>
  );
}
