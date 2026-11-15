import { useRef, useState } from "react";
import { ArrowUp, Paperclip } from "lucide-react";

export default function ChatInput({ onSend, onAttachClick, disabled, placeholder }) {
  const [val, setVal] = useState("");
  const ref = useRef(null);
  const hasText = val.trim().length > 0;

  function send() {
    if (!val.trim() || disabled) return;
    onSend(val.trim());
    setVal("");
    if (ref.current) ref.current.style.height = "auto";
  }

  return (
    <div className={`flex items-end gap-2 bg-white border rounded-2xl p-2 transition-all duration-150 ${hasText ? "border-forest-400 shadow-lift" : "border-stone-200 shadow-card"}`}>
      <button onClick={onAttachClick} type="button" aria-label="Upload" title="Upload document"
        className="shrink-0 w-10 h-10 grid place-items-center rounded-xl text-stone-400 hover:text-forest-700 hover:bg-forest-50 transition-colors cursor-pointer">
        <Paperclip size={17} />
      </button>
      <textarea ref={ref} rows={1} value={val} disabled={disabled}
        placeholder={placeholder || "Ask about your legal rights..."}
        onChange={e => { setVal(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px"; }}
        onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
        className="flex-1 resize-none bg-transparent outline-none text-[15px] text-stone-800 placeholder:text-stone-400 py-2 max-h-36 disabled:opacity-50 font-body" />
      <button onClick={send} disabled={!hasText || disabled} type="button" aria-label="Send"
        className={`shrink-0 w-10 h-10 grid place-items-center rounded-xl transition-all duration-150 cursor-pointer ${hasText ? "bg-forest-700 text-white hover:bg-forest-600" : "bg-stone-100 text-stone-400"} disabled:cursor-not-allowed`}>
        <ArrowUp size={17} />
      </button>
    </div>
  );
}
