// Free-tier message gating. Swap this for a server-side check once
// accounts exist — client-side counting is trivially resettable, fine
// for a soft nudge toward signup, not for hard enforcement.
const KEY = "nyayai_free_msgs_used";
export const FREE_LIMIT = 3;

export function getUsed() {
  return parseInt(localStorage.getItem(KEY) || "0", 10);
}

export function increment() {
  const next = getUsed() + 1;
  localStorage.setItem(KEY, String(next));
  return next;
}

export function remaining() {
  return Math.max(0, FREE_LIMIT - getUsed());
}

export function reset() {
  localStorage.removeItem(KEY);
}
