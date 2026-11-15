import { useState } from "react";
import { Plus } from "lucide-react";

const FAQS = [
  {
    q: "Is this a substitute for a lawyer?",
    a: "No. NyayAI gives you legal information grounded in the actual text of the law, so you understand your situation and your options. For representation, drafting, or anything contested, you still need a licensed advocate.",
  },
  {
    q: "Is it actually free?",
    a: "Yes — your first 3 questions need no account at all. Beyond that, a free sign-in keeps it going. There's no paywall on the legal information itself.",
  },
  {
    q: "Which languages does it support?",
    a: "English, Hindi, and Marathi — for both typed questions and photos of documents you upload.",
  },
  {
    q: "How is this different from asking ChatGPT?",
    a: "General AI tools answer from training data and can invent provisions that don't exist. NyayAI retrieves the actual relevant section of the actual Act first, then answers from that — and shows you the citation so you can verify it yourself.",
  },
  {
    q: "Is my data private?",
    a: "The system runs on self-hosted, open models — your questions aren't routed through a third-party AI vendor's API.",
  },
];

export default function FaqAccordion() {
  const [open, setOpen] = useState(0);

  return (
    <div className="max-w-2xl mx-auto divide-y divide-ink/10">
      {FAQS.map((item, i) => {
        const isOpen = open === i;
        return (
          <div key={item.q} className="py-1">
            <button
              onClick={() => setOpen(isOpen ? -1 : i)}
              className="w-full flex items-center justify-between gap-4 py-5 text-left cursor-pointer group"
              aria-expanded={isOpen}
            >
              <span className="font-display text-lg text-ink group-hover:text-brass-700 transition-colors">
                {item.q}
              </span>
              <Plus
                size={18}
                className={`shrink-0 text-ink-600 transition-transform duration-300 ${
                  isOpen ? "rotate-45 text-brass-700" : ""
                }`}
              />
            </button>
            <div
              className="grid transition-all duration-300 ease-out"
              style={{ gridTemplateRows: isOpen ? "1fr" : "0fr" }}
            >
              <div className="overflow-hidden">
                <p className="text-sm text-ink-600 leading-relaxed pb-5 max-w-xl">
                  {item.a}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
