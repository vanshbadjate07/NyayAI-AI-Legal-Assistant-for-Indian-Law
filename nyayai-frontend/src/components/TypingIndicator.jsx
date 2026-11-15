export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-2.5 px-1">
      {[0, 1, 2].map(i => (
        <span key={i} className="w-2 h-2 rounded-full bg-forest-400 animate-dot"
          style={{ animationDelay: `${i * 0.2}s` }} />
      ))}
    </div>
  );
}
