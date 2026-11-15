import { useState } from "react";
import { Scale, User, FileText, ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const VL = { rti:"RTI", tenancy:"Tenancy", consumer:"Consumer", family:"Family Law", criminal:"Criminal", general:"General" };

function ts(t) {
  if (!t) return "";
  return new Date(t).toLocaleTimeString("en-IN", { hour:"2-digit", minute:"2-digit", hour12:true });
}

function MD({ content }) {
  return (
    <div className="chat-prose text-[15px] text-stone-700 leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{
          p:({ children })=><p>{children}</p>,
          strong:({ children })=><strong className="font-semibold text-stone-900">{children}</strong>,
          ul:({ children })=><ul>{children}</ul>,
          ol:({ children })=><ol>{children}</ol>,
          li:({ children })=><li>{children}</li>,
          code:({ children })=><code>{children}</code>,
          blockquote:({ children })=><blockquote>{children}</blockquote>,
        }}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default function ChatBubble({ message }) {
  const [srcOpen, setSrcOpen] = useState(false);
  const isUser = message.role === "user";

  if (isUser) return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-end gap-2">
        <div className="max-w-[75%] sm:max-w-[65%] bg-forest-700 text-white text-[15px] leading-relaxed px-4 py-3 rounded-2xl rounded-br-sm">
          {message.content}
        </div>
        <div className="w-8 h-8 rounded-full bg-stone-200 grid place-items-center shrink-0">
          <User size={14} className="text-stone-500" />
        </div>
      </div>
      {message.ts && <span className="text-[11px] text-stone-400 mr-10">{ts(message.ts)}</span>}
    </div>
  );

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex items-end gap-2">
        <div className="w-8 h-8 rounded-full bg-forest-50 border border-forest-200 grid place-items-center shrink-0">
          <Scale size={14} className="text-forest-700" />
        </div>
        <div className="max-w-[85%] sm:max-w-[75%] space-y-2">
          {message.error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl rounded-tl-sm px-4 py-3 text-sm">{message.content}</div>
          ) : (
            <div className="bg-white border border-stone-200 rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-card">
              {message.vertical && (
                <span className="inline-block text-[10px] font-semibold uppercase tracking-widest text-forest-700 bg-forest-50 border border-forest-200 px-2 py-0.5 rounded-full mb-3">
                  {VL[message.vertical] || message.vertical}
                </span>
              )}
              <MD content={message.content} />
              {message.warning && (
                <div className="mt-3 flex gap-2 items-start bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
                  <AlertTriangle size={13} className="text-amber-600 shrink-0 mt-0.5" />
                  <p className="text-[12px] text-amber-800 leading-relaxed">{message.warning}</p>
                </div>
              )}
            </div>
          )}
          {message.sources?.length > 0 && (
            <button onClick={() => setSrcOpen(o => !o)}
              className="flex items-center gap-1.5 text-[11px] text-stone-400 hover:text-forest-700 transition-colors cursor-pointer">
              <FileText size={11} />
              {message.sources.length} source{message.sources.length > 1 ? "s" : ""} cited
              {srcOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
          )}
          {srcOpen && message.sources?.map((s, i) => (
            <div key={i} className="text-xs bg-stone-50 border border-stone-200 rounded-xl px-3 py-2.5">
              <div className="flex items-start gap-2 mb-1">
                <div className="font-semibold text-stone-700 flex-1">
                  {s.act || s.source}
                  {s.section && s.section !== "N/A" && <> · {s.section}</>}
                  {s.section_title && <span className="font-normal text-stone-500"> — {s.section_title}</span>}
                </div>
                <span className="shrink-0 text-[10px] text-stone-400 tabular-nums" title="cosine similarity to your question">
                  {typeof s.score === "number" ? s.score.toFixed(3) : ""}
                </span>
              </div>
              <div className="text-[10px] text-stone-400 mb-1.5">
                {s.source}{s.page ? ` · page ${s.page}` : ""}
              </div>
              <div className="text-stone-500 line-clamp-4">{s.text}</div>
            </div>
          ))}
          {message.disclaimer && (
            <p className="text-[11px] text-stone-400 italic pt-0.5">{message.disclaimer}</p>
          )}
        </div>
      </div>
      {message.ts && <span className="text-[11px] text-stone-400 ml-10">{ts(message.ts)}</span>}
    </div>
  );
}
