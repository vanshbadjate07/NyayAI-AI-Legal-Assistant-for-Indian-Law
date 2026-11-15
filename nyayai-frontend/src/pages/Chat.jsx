import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Scale, Plus, Search, Trash2, Pencil, Check, X as XIcon, Menu, Landmark, Home as HomeIcon, ShoppingBag, Users, Gavel, FileSearch } from "lucide-react";
import ChatBubble from "../components/ChatBubble.jsx";
import ChatInput from "../components/ChatInput.jsx";
import TypingIndicator from "../components/TypingIndicator.jsx";
import LoginModal from "../components/LoginModal.jsx";
import UploadModal from "../components/UploadModal.jsx";
import { useAuth } from "../lib/auth.jsx";
import { getHealth, postQuery, postUpload } from "../lib/api.js";
import * as chatLimit from "../lib/chatLimit.js";
import * as history from "../lib/chatHistory.js";

const SUGGESTIONS = [
  { icon: FileSearch,  text: "How do I file an RTI application?" },
  { icon: HomeIcon,    text: "Landlord won't return my security deposit" },
  { icon: ShoppingBag, text: "I received a defective product — what are my rights?" },
  { icon: Users,       text: "How to claim maintenance after divorce?" },
  { icon: Gavel,       text: "Police refused to register my FIR — what can I do?" },
  { icon: Landmark,    text: "How long can PIO take to respond to RTI?" },
];

function fmt(ts) {
  if (!ts) return "";
  const d = new Date(ts), now = new Date(), diff = now - d;
  if (diff < 86400000) return d.toLocaleTimeString("en-IN", { hour:"2-digit", minute:"2-digit", hour12:true });
  if (diff < 604800000) return d.toLocaleDateString("en-IN", { weekday:"short" });
  return d.toLocaleDateString("en-IN", { day:"numeric", month:"short" });
}

function ChatItem({ chat, active, onSelect, onDelete, onRename }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(chat.title);
  const iRef = useRef(null);

  function startEdit(e) { e.stopPropagation(); setEditing(true); setTimeout(() => iRef.current?.focus(), 20); }
  function commit(e) { e?.stopPropagation(); onRename(chat.id, val || chat.title); setEditing(false); }
  function cancel(e) { e?.stopPropagation(); setVal(chat.title); setEditing(false); }

  return (
    <div onClick={() => !editing && onSelect(chat.id)} title={`Created ${new Date(chat.createdAt).toLocaleString("en-IN")}`}
      className={`group relative flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-100 select-none ${
        active ? "bg-forest-50 border border-forest-200" : "hover:bg-stone-100 border border-transparent"
      }`}>
      {editing ? (
        <input ref={iRef} value={val} onChange={e => setVal(e.target.value)} onClick={e => e.stopPropagation()}
          onKeyDown={e => { if (e.key === "Enter") commit(); if (e.key === "Escape") cancel(); }}
          className="flex-1 text-sm bg-white border border-forest-300 rounded-lg px-2 py-0.5 outline-none text-stone-800 min-w-0" />
      ) : (
        <span className={`flex-1 text-sm truncate min-w-0 ${active ? "text-forest-800 font-medium" : "text-stone-600"}`}>{chat.title}</span>
      )}
      <div className={`flex items-center gap-0.5 shrink-0 transition-opacity ${editing ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
        {editing ? (
          <>
            <button onClick={commit} className="w-6 h-6 grid place-items-center rounded text-forest-700 hover:bg-forest-100 cursor-pointer"><Check size={12} /></button>
            <button onClick={cancel} className="w-6 h-6 grid place-items-center rounded text-stone-400 hover:bg-stone-200 cursor-pointer"><XIcon size={12} /></button>
          </>
        ) : (
          <>
            <button onClick={startEdit} title="Rename" className="w-6 h-6 grid place-items-center rounded text-stone-400 hover:text-stone-700 hover:bg-stone-200 cursor-pointer"><Pencil size={11} /></button>
            <button onClick={e => { e.stopPropagation(); onDelete(chat.id); }} title="Delete" className="w-6 h-6 grid place-items-center rounded text-stone-400 hover:text-red-600 hover:bg-red-50 cursor-pointer"><Trash2 size={11} /></button>
          </>
        )}
      </div>
      {!editing && <span className="absolute right-2 top-1 text-[9px] text-stone-400 hidden group-hover:block">{fmt(chat.updatedAt)}</span>}
    </div>
  );
}

function Sidebar({ chats, activeChatId, onNew, onSelect, onDelete, onRename, user, onLoginClick, onClose, mobile }) {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const { logout } = useAuth();
  const filtered = q.trim() ? chats.filter(c => c.title.toLowerCase().includes(q.toLowerCase())) : chats;

  return (
    <aside className="flex flex-col h-full bg-white border-r border-stone-200 w-64">
      <div className="flex items-center justify-between px-4 py-4 border-b border-stone-100">
        <button onClick={() => navigate("/")} className="flex items-center gap-2 cursor-pointer hover:opacity-70 transition-opacity">
          <div className="w-7 h-7 rounded-lg bg-forest-700 grid place-items-center"><Scale size={13} className="text-white" /></div>
          <span className="font-display text-base font-semibold text-stone-800">Nyay<span className="text-forest-700">AI</span></span>
        </button>
        {mobile && <button onClick={onClose} className="text-stone-400 hover:text-stone-700 cursor-pointer"><XIcon size={18} /></button>}
      </div>

      <div className="px-3 pt-3">
        <button onClick={onNew}
          className="w-full flex items-center gap-2 border border-stone-200 rounded-xl px-3 py-2.5 text-sm font-semibold text-stone-600 hover:bg-stone-50 hover:text-forest-700 hover:border-forest-300 transition-all cursor-pointer">
          <Plus size={14} /> New chat
        </button>
      </div>

      <div className="px-3 pt-2.5">
        <div className="flex items-center gap-2 bg-stone-50 border border-stone-200 rounded-xl px-3 py-2">
          <Search size={13} className="text-stone-400 shrink-0" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search chats..."
            className="flex-1 bg-transparent text-sm text-stone-700 outline-none placeholder:text-stone-400" />
        </div>
      </div>

      {chats.length > 0 && (
        <p className="px-4 pt-3 pb-1 text-[10px] font-semibold text-stone-400 uppercase tracking-wider">Recent</p>
      )}
      <div className="flex-1 overflow-y-auto thin-scroll px-3 pb-2 space-y-0.5">
        {filtered.length === 0 && (
          <p className="text-xs text-stone-400 text-center py-8">{q ? "No matching chats" : "No chats yet"}</p>
        )}
        {filtered.map(c => (
          <ChatItem key={c.id} chat={c} active={c.id === activeChatId}
            onSelect={onSelect} onDelete={onDelete} onRename={onRename} />
        ))}
      </div>

      <div className="border-t border-stone-100 px-3 py-3">
        {user ? (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-forest-100 border border-forest-200 grid place-items-center text-xs font-bold text-forest-700 shrink-0">
              {user.name?.[0]?.toUpperCase() || "U"}
            </div>
            <span className="text-xs text-stone-500 truncate flex-1">{user.email}</span>
            <button onClick={logout} className="text-[10px] text-stone-400 hover:text-stone-700 cursor-pointer transition-colors">out</button>
          </div>
        ) : (
          <button onClick={onLoginClick}
            className="w-full text-xs text-forest-700 hover:text-forest-800 text-center py-1 cursor-pointer transition-colors font-medium">
            Sign in for unlimited questions →
          </button>
        )}
      </div>
    </aside>
  );
}

export default function Chat() {
  const { user } = useAuth();
  const [chats, setChats] = useState(() => history.getAllChats());
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [thinking, setThinking] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginReason, setLoginReason] = useState("limit");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [backendDown, setBackendDown] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { getHealth().catch(() => setBackendDown(true)); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages, thinking]);

  const refreshChats = useCallback(() => setChats(history.getAllChats()), []);

  function newChat() { setActiveChatId(null); setMessages([]); setSidebarOpen(false); }
  function selectChat(id) {
    const c = history.getChat(id);
    if (!c) return;
    setActiveChatId(id); setMessages(c.messages || []); setSidebarOpen(false);
  }
  function deleteChat(id) { history.deleteChat(id); refreshChats(); if (id === activeChatId) newChat(); }
  function renameChat(id, t) { history.renameChat(id, t); refreshChats(); }
  function freeLimitReached() { return !user && chatLimit.remaining() <= 0; }

  async function handleSend(text) {
    if (freeLimitReached()) { setLoginReason("limit"); setLoginOpen(true); return; }
    const userMsg = { role:"user", content:text, ts:Date.now() };
    const next = [...messages, userMsg];
    setMessages(next);
    if (!user) chatLimit.increment();
    setThinking(true);
    let chatId = activeChatId;
    if (!chatId) { chatId = history.createChat(text); setActiveChatId(chatId); }
    history.saveMessages(chatId, next); refreshChats();
    try {
      const res = await postQuery(text);
      const aiMsg = { role:"assistant", content:res.answer, vertical:res.vertical, language:res.language, sources:res.sources, disclaimer:res.disclaimer, warning:res.warning, abstained:res.abstained, ts:Date.now() };
      const final = [...next, aiMsg];
      setMessages(final); history.saveMessages(chatId, final); refreshChats();
    } catch(e) {
      const errMsg = { role:"assistant", content:e.message, error:true, ts:Date.now() };
      setMessages([...next, errMsg]);
    } finally { setThinking(false); }
  }

  async function handleUpload(file) {
    if (!user) { setLoginReason("upload"); setLoginOpen(true); return; }
    setUploading(true);
    setMessages(m => [...m, { role:"user", content:`📎 ${file.name}`, ts:Date.now() }]);
    try {
      const res = await postUpload(file);
      setMessages(m => [...m, { role:"assistant", content:res.answer || `Extracted:\n\n${res.extracted_text}`, vertical:res.vertical, language:res.detected_language, sources:res.sources, disclaimer:res.disclaimer, warning:res.warning, abstained:res.abstained, ts:Date.now() }]);
    } catch(e) {
      setMessages(m => [...m, { role:"assistant", content:e.message, error:true, ts:Date.now() }]);
    } finally { setUploading(false); setUploadOpen(false); }
  }

  const remaining = !user ? chatLimit.remaining() : null;
  const currentTitle = activeChatId ? chats.find(c => c.id === activeChatId)?.title : null;

  return (
    <div className="h-screen flex overflow-hidden bg-stone-50">
      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSidebarOpen(false)} />
          <div className="relative z-10"><Sidebar chats={chats} activeChatId={activeChatId} onNew={newChat} onSelect={selectChat} onDelete={deleteChat} onRename={renameChat} user={user} onLoginClick={() => { setLoginReason("limit"); setLoginOpen(true); }} mobile onClose={() => setSidebarOpen(false)} /></div>
        </div>
      )}
      {/* Desktop sidebar */}
      <div className="hidden lg:block h-full shrink-0">
        <Sidebar chats={chats} activeChatId={activeChatId} onNew={newChat} onSelect={selectChat} onDelete={deleteChat} onRename={renameChat} user={user} onLoginClick={() => { setLoginReason("limit"); setLoginOpen(true); }} />
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 sm:px-6 h-14 border-b border-stone-200 bg-white shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-stone-400 hover:text-stone-700 cursor-pointer transition-colors"><Menu size={20} /></button>
          <p className="flex-1 text-sm text-stone-500 truncate">{currentTitle || "New conversation"}</p>
          {backendDown && <span className="text-xs text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">Backend offline</span>}
          {remaining !== null && remaining > 0 && <span className="text-xs text-stone-400 hidden sm:block">{remaining} free remaining</span>}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto thin-scroll">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center px-6 py-12 text-center max-w-2xl mx-auto">
              <div className="w-14 h-14 rounded-2xl bg-forest-700 grid place-items-center mx-auto mb-5">
                <Scale size={26} className="text-white" />
              </div>
              <h2 className="font-display text-3xl sm:text-4xl text-stone-900 mb-2">What's your legal question?</h2>
              <p className="text-stone-500 text-sm mb-8 max-w-sm leading-relaxed">Ask in English, Hindi, or Marathi. Answers grounded in real Indian Acts, every claim cited.</p>
              <div className="grid sm:grid-cols-2 gap-2.5 w-full max-w-xl">
                {SUGGESTIONS.map(s => (
                  <button key={s.text} onClick={() => handleSend(s.text)}
                    className="flex items-start gap-2.5 text-left text-sm bg-white border border-stone-200 rounded-xl px-4 py-3 text-stone-600 hover:border-forest-300 hover:text-forest-800 hover:bg-forest-50 transition-all duration-150 group cursor-pointer shadow-card">
                    <s.icon size={14} className="text-forest-500 shrink-0 mt-0.5" /> {s.text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">
              {messages.map((m, i) => <ChatBubble key={i} message={m} />)}
              {thinking && (
                <div className="flex items-end gap-2">
                  <div className="w-8 h-8 rounded-full bg-forest-50 border border-forest-200 grid place-items-center shrink-0">
                    <Scale size={14} className="text-forest-700" />
                  </div>
                  <div className="bg-white border border-stone-200 rounded-2xl rounded-tl-sm px-4 shadow-card">
                    <TypingIndicator />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="shrink-0 border-t border-stone-200 bg-white px-4 sm:px-6 py-4">
          {remaining !== null && remaining <= 0 && (
            <p className="text-center text-xs text-forest-700 mb-2.5 cursor-pointer hover:text-forest-800"
              onClick={() => { setLoginReason("limit"); setLoginOpen(true); }}>
              Free limit reached — sign in to keep asking →
            </p>
          )}
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={handleSend}
              onAttachClick={() => user ? setUploadOpen(true) : (setLoginReason("upload"), setLoginOpen(true))}
              disabled={thinking || freeLimitReached()}
              placeholder={freeLimitReached() ? "Sign in to keep asking..." : "Ask about your legal rights..."} />
            <p className="text-center text-[11px] text-stone-400 mt-2">NyayAI provides legal information, not advice.</p>
          </div>
        </div>
      </div>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} reason={loginReason} />
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} onUpload={handleUpload} loading={uploading} />
    </div>
  );
}
