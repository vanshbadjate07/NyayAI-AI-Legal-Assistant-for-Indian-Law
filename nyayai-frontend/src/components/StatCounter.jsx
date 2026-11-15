import { useEffect, useRef, useState } from "react";
import { useInView } from "framer-motion";

export default function StatCounter({ value, suffix = "", label, icon: Icon }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const duration = 1200;
    const start = performance.now();
    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * value));
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [inView, value]);

  return (
    <div ref={ref} className="text-center">
      {Icon && <Icon size={20} className="text-brass-400 mx-auto mb-3" />}
      <div className="font-display text-4xl sm:text-5xl text-parchment-100 tabular-nums">
        {count}
        <span className="text-brass-400">{suffix}</span>
      </div>
      <div className="text-sm text-parchment-300/60 mt-2">{label}</div>
    </div>
  );
}
