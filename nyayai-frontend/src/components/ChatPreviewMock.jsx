import { Scale, User, FileText } from "lucide-react";

export default function ChatPreviewMock() {
  return (
    <div className="glass-card rounded-2xl p-4 sm:p-5 shadow-stamp w-full max-w-sm">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-parchment-100/10">
        <span className="w-2 h-2 rounded-full bg-jade-400" />
        <span className="text-xs text-parchment-300/50 font-mono">
          live answer preview
        </span>
      </div>

      <div className="flex justify-end mb-3">
        <div className="bg-brass/90 text-ink-950 rounded-2xl rounded-tr-sm px-3.5 py-2 text-[13px] max-w-[80%]">
          Landlord won't return my deposit, what now?
        </div>
      </div>

      <div className="flex gap-2">
        <div className="w-6 h-6 rounded-full bg-brass/20 grid place-items-center shrink-0 mt-0.5">
          <Scale size={12} className="text-brass-300" />
        </div>
        <div className="space-y-2">
          <div className="bg-ink-700/80 border border-parchment-100/10 rounded-2xl rounded-tl-sm px-3.5 py-2.5 text-[13px] text-parchment-200/90 leading-relaxed">
            Under the <strong className="text-parchment-100">Maharashtra Rent
            Control Act</strong>, your landlord must refund the deposit within
            the period agreed in writing — usually at vacancy...
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-jade-300/70 pl-1">
            <FileText size={11} />
            Section 106 · Maharashtra Rent Control Act 1999
          </div>
        </div>
      </div>
    </div>
  );
}
