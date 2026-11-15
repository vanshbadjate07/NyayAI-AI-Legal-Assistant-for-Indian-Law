export default function Button({ as: Comp = "button", variant = "primary", size = "md", className = "", children, ...props }) {
  const base = "inline-flex items-center justify-center gap-2 font-body font-semibold rounded-full transition-all duration-200 focus-visible:outline-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer";
  const sizes = { md: "px-7 py-3 text-[15px] min-h-[48px]", sm: "px-5 py-2.5 text-sm min-h-[40px]" };
  const variants = {
    primary: "bg-gold text-night shadow-glow hover:bg-gold-300 hover:-translate-y-0.5 active:translate-y-0",
    ghost:   "bg-transparent text-ivory border border-white/15 hover:border-white/30 hover:bg-white/5",
    danger:  "bg-crimson/20 text-red-400 border border-crimson/30 hover:bg-crimson/30",
  };
  return (
    <Comp className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </Comp>
  );
}
