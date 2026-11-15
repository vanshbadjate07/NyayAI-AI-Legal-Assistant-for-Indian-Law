import { useState } from "react";
import { Plus, Search, Trash2, Pencil, MessageSquare, Check, X, Scale } from "lucide-react";
import * as history from "../lib/chatHistory.js";

function timeAgo(ts) {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function formatDate(ts) {
  return new Date(ts).toLocaleString("en-IN", { day:"numeric", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit" });
}

export default function ChatSidebar({ chats, activeChatId, onSelect, onNew, onDelete, onRename, open, onClose }) {
  const [search, setSearch] = useState("");
  const [editId, setEditId] = useState(null);
  const [editVal, setEditVal] = useState("");

  const filtered = chats.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  function startRename(c, e) {
    e.stopPropagation();
    setEditId(c.id);
    setEditVal(c.title);
  }
  function commitRename(id) {
    if (editVal.trim()) onRename(id, editVal.trim());
    setEditId(null);
  }

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div className="fixed inset-0 bg-black/60 z-30 lg:hidden" onClick={onClose}/>
      )}

      <aside className={`fixed lg:relative inset-y-0 left-0 z-40 lg:z-auto w-72 bg-night-800 border-r border-white/5 flex flex-col transition-transform duration-300 ${open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        {/* header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Scale size={15} className="text-gold-400"/>
            <span className="font-display text-base text-ivory">NyayAI</span>
          </div>
          <button onClick={onClose} className="lg:hidden text-ivory/40 hover:text-ivory cursor-pointer p-1">
            <X size={16}/>
          </button>
        </div>

        {/* new chat */}
        <div className="px-3 py-3 border-b border-white/5">
          <button onClick={onNew}
            className="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-gold/10 border border-gold/20 text-gold-400 text-sm font-semibold hover:bg-gold/18 transition-colors cursor-pointer group">
            <Plus size={15} className="group-hover:rotate-90 transition-transform duration-200"/>
            New chat
          </button>
        </div>

        {/* search */}
        <div className="px-3 py-2.5 border-b border-white/5">
          <div className="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-2">
            <Search size={13} className="text-ivory/30 shrink-0"/>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats..."
              className="bg-transparent text-sm text-ivory placeholder:text-ivory/30 outline-none w-full"
            />
            {search && (
              <button onClick={() => setSearch("")} className="text-ivory/30 hover:text-ivory cursor-pointer"><X size={12}/></button>
            )}
          </div>
        </div>

        {/* chat list */}
        <div className="flex-1 overflow-y-auto scrollbar-thin py-2">
          {filtered.length === 0 ? (
            <div className="text-center py-10 text-ivory-dim text-sm px-4">
              {search ? "No chats match your search" : "No chats yet — start a new conversation"}
            </div>
          ) : (
            filtered.map((c) => (
              <div key={c.id} className={`group relative mx-2 my-0.5 rounded-xl transition-colors duration-150 ${activeChatId === c.id ? "bg-gold/12 border border-gold/20" : "hover:bg-white/5 border border-transparent"}`}>
                <button onClick={() => { onSelect(c.id); onClose(); }}
                  className="w-full text-left px-3.5 py-3 cursor-pointer pr-16">
                  {editId === c.id ? (
                    <input
                      autoFocus
                      value={editVal}
                      onChange={(e) => setEditVal(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") commitRename(c.id); if (e.key === "Escape") setEditId(null); }}
                      onClick={(e) => e.stopPropagation()}
                      className="bg-white/10 border border-gold/30 rounded-md px-2 py-0.5 text-sm text-ivory outline-none w-full"
                    />
                  ) : (
                    <span className="block truncate text-sm text-ivory/80 font-medium" title={c.title}>{c.title}</span>
                  )}
                  <div className="flex items-center gap-1.5 mt-1">
                    <MessageSquare size={10} className="text-ivory/25"/>
                    <time className="text-[11px] text-ivory/30" title={formatDate(c.updatedAt)}>
                      {timeAgo(c.updatedAt)}
                    </time>
                  </div>
                </button>
                {/* action buttons — show on hover */}
                {editId === c.id ? (
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                    <button onClick={(e) => { e.stopPropagation(); commitRename(c.id); }} className="w-7 h-7 grid place-items-center rounded-lg bg-gold/20 text-gold-400 hover:bg-gold/30 cursor-pointer"><Check size={12}/></button>
                    <button onClick={(e) => { e.stopPropagation(); setEditId(null); }} className="w-7 h-7 grid place-items-center rounded-lg bg-white/5 text-ivory/40 hover:text-ivory cursor-pointer"><X size={12}/></button>
                  </div>
                ) : (
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={(e) => startRename(c, e)} className="w-7 h-7 grid place-items-center rounded-lg hover:bg-white/10 text-ivory/40 hover:text-ivory cursor-pointer" title="Rename"><Pencil size={12}/></button>
                    <button onClick={(e) => { e.stopPropagation(); onDelete(c.id); }} className="w-7 h-7 grid place-items-center rounded-lg hover:bg-red-500/15 text-ivory/40 hover:text-red-400 cursor-pointer" title="Delete"><Trash2 size={12}/></button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}
