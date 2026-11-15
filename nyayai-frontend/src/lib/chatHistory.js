const KEY = "nyayai_chat_history";

function load() {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
  catch { return []; }
}

function save(chats) {
  localStorage.setItem(KEY, JSON.stringify(chats));
}

export function getAllChats() {
  return load().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getChat(id) {
  return load().find((c) => c.id === id) || null;
}

export function createChat(firstMessage) {
  const id = crypto.randomUUID();
  const now = Date.now();
  const title = firstMessage.slice(0, 42) + (firstMessage.length > 42 ? "…" : "");
  const chats = load();
  chats.unshift({ id, title, messages: [], createdAt: now, updatedAt: now });
  save(chats);
  return id;
}

export function saveMessages(id, messages) {
  const chats = load();
  const idx = chats.findIndex((c) => c.id === id);
  if (idx !== -1) { chats[idx].messages = messages; chats[idx].updatedAt = Date.now(); }
  save(chats);
}

export function renameChat(id, title) {
  const chats = load();
  const idx = chats.findIndex((c) => c.id === id);
  if (idx !== -1) chats[idx].title = title;
  save(chats);
}

export function deleteChat(id) {
  save(load().filter((c) => c.id !== id));
}
