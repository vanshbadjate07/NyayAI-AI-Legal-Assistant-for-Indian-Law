import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Scale, ArrowRight, Shield, BookOpen, Landmark, Home as HomeIcon, ShoppingBag, Users, Gavel, Languages, CheckCircle2, FileText } from "lucide-react";
import Navbar from "../components/Navbar.jsx";
import LoginModal from "../components/LoginModal.jsx";

function useReveal() {
  const ref = useRef(null);
  const [v, setV] = useState(false);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setV(true); obs.disconnect(); } }, { threshold: 0.1 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return [ref, v];
}

function Reveal({ children, delay = 0 }) {
  const [ref, v] = useReveal();
  return (
    <div ref={ref} style={{ opacity: v ? 1 : 0, transform: v ? "none" : "translateY(18px)", transition: `opacity .5s ease ${delay}ms, transform .5s cubic-bezier(.16,1,.3,1) ${delay}ms` }}>
      {children}
    </div>
  );
}

function Counter({ to, suffix = "" }) {
  const [n, setN] = useState(0);
  const [ref, v] = useReveal();
  useEffect(() => {
    if (!v) return;
    let i = 0;
    const step = Math.ceil(to / 50);
    const t = setInterval(() => { i = Math.min(i + step, to); setN(i); if (i >= to) clearInterval(t); }, 18);
    return () => clearInterval(t);
  }, [v, to]);
  return <span ref={ref}>{n}{suffix}</span>;
}

const VERTICALS = [
  { icon: Landmark,    name: "Right to Information", desc: "File RTI applications, track appeals, understand PIO deadlines.", law: "RTI Act 2005" },
  { icon: HomeIcon,    name: "Tenancy & Rent",        desc: "Security deposits, eviction, rent agreements and disputes.", law: "Model Tenancy Act 2021 \u00b7 MH Rent Control 1999" },
  { icon: ShoppingBag, name: "Consumer Protection",   desc: "Defective products, refunds, NCDRC complaint procedures.", law: "CPA 2019" },
  { icon: Users,       name: "Family Law",            desc: "Maintenance, divorce, domestic violence, matrimonial rights.", law: "HMA 1955 · DV Act 2005" },
  { icon: Gavel,       name: "Criminal Law",          desc: "FIR rights, bail, BNS and BNSS provisions (new criminal codes).", law: "BNS · BNSS 2023" },
];

const STEPS = [
  { n: "1", title: "Ask in plain language", desc: "Type your situation in English, Hindi, or Marathi. No legal jargon needed — explain it like you would to a friend." },
  { n: "2", title: "We retrieve the actual law", desc: "Your question is matched against real Indian Acts stored in our knowledge base — not general AI training data." },
  { n: "3", title: "Get a cited answer", desc: "You receive a clear explanation with the exact section number cited, so you can verify it yourself." },
];

const HONESTY = [
  { good: true,  text: "Answers are generated only from the nine Indian Acts indexed in the knowledge base \u2014 not from general model knowledge." },
  { good: true,  text: "Every answer lists the sections it used, with the Act name and page, so you can read the original text yourself." },
  { good: true,  text: "If the retrieved law does not cover your question, NyayAI says so and points you to free legal aid instead of guessing." },
  { good: false, text: "It does not cover tax, immigration, labour, property-title or corporate law. Those Acts are not indexed." },
  { good: false, text: "It gives legal information, not legal advice. It will not predict the outcome of your specific case." },
  { good: false, text: "Answers are produced by a small local language model and can be incomplete. Verify anything important against the cited section." },
];

// Static sample answer card — no animation, no sizing bugs
function SampleAnswer() {
  return (
    <div className="bg-white border border-stone-200 rounded-2xl shadow-lift overflow-hidden max-w-md w-full">
      <div className="bg-stone-50 border-b border-stone-200 px-4 py-3 flex items-center gap-2">
        <div className="w-6 h-6 rounded-md bg-forest-700 grid place-items-center"><Scale size={12} className="text-white" /></div>
        <span className="text-sm font-semibold text-stone-700">NyayAI</span>
        <span className="ml-auto text-xs bg-forest-50 text-forest-700 border border-forest-200 px-2 py-0.5 rounded-full font-medium">RTI Act</span>
      </div>
      <div className="p-5 space-y-4">
        <div className="flex justify-end">
          <div className="bg-forest-700 text-white text-sm px-4 py-2.5 rounded-2xl rounded-br-sm max-w-[85%]">
            How long can PIO take to respond to my RTI?
          </div>
        </div>
        <div className="text-sm text-stone-700 leading-relaxed border-l-2 border-forest-500 pl-4 bg-forest-50 py-3 pr-3 rounded-r-xl">
          Under <strong className="text-forest-800">Section 7(1)</strong> of the RTI Act 2005, the PIO must respond within <strong className="text-forest-800">30 days</strong>. If it concerns life or liberty, the deadline is <strong className="text-forest-800">48 hours</strong>. You can file a first appeal under Section 19 if the deadline is missed.
        </div>
        <div className="flex items-center gap-1.5">
          <FileText size={11} className="text-stone-400" />
          <span className="text-xs text-stone-400">Example · RTI Act 2005, Sections 7 and 19</span>
        </div>
      </div>
    </div>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const [loginOpen, setLoginOpen] = useState(false);
  const [statsRef, statsV] = useReveal();

  return (
    <div className="min-h-screen bg-stone-50">
      <Navbar onLoginClick={() => setLoginOpen(true)} />

      {/* HERO */}
      <section className="relative overflow-hidden border-b border-stone-200">
        {/* Subtle background texture */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(27,92,69,0.08),transparent)] pointer-events-none" />

        <div className="max-w-6xl mx-auto px-5 sm:px-8 py-16 sm:py-24 grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <div className="stagger">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-forest-700 bg-forest-50 border border-forest-200 px-3 py-1.5 rounded-full mb-6">
              <Scale size={11} /> Free · AI-powered · India
            </span>
            <h1 className="font-display text-[3rem] sm:text-[4rem] lg:text-[4.5rem] leading-[1.0] text-stone-900 mb-5">
              Justice shouldn't<br />
              <span className="text-forest-gradient italic">cost a lawyer's fee.</span>
            </h1>
            <p className="text-lg text-stone-500 leading-relaxed mb-8 max-w-lg">
              Ask any legal question in English, Hindi, or Marathi and get answers grounded in actual Indian law — RTI Act, Tenancy, Consumer Protection, Family Law, BNS/BNSS — with the exact section cited.
            </p>
            <div className="flex flex-wrap gap-3 items-center mb-10">
              <button onClick={() => navigate("/chat")}
                className="inline-flex items-center gap-2 bg-forest-700 text-white font-semibold px-7 py-3.5 rounded-full hover:bg-forest-600 transition-colors shadow-lift cursor-pointer">
                Start free — no account needed <ArrowRight size={15} />
              </button>
            </div>
            <div className="flex items-center gap-6 pt-6 border-t border-stone-200">
              {[["3", "languages"], ["9", "Acts indexed"], ["5", "legal domains"]].map(([v, l]) => (
                <div key={l}>
                  <div className="font-display text-2xl text-forest-700 font-semibold">{v}</div>
                  <div className="text-xs text-stone-500">{l}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Static sample answer — no animation, no sizing issues */}
          <div className="flex justify-center lg:justify-end">
            <SampleAnswer />
          </div>
        </div>
      </section>

      {/* STATS BAND */}
      <section ref={statsRef} className="border-b border-stone-200 bg-white py-12">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
          {[{ v:9,s:"",l:"Acts indexed" }, { v:5,s:"",l:"Legal domains" }, { v:3,s:"",l:"Languages supported" }, { v:5,s:"",l:"Sections cited per answer" }].map((item) => (
            <div key={item.l}>
              <div className="font-display text-4xl sm:text-5xl text-forest-gradient font-semibold leading-none mb-1">
                {statsV ? <Counter to={item.v} suffix={item.s} /> : "0"}
              </div>
              <div className="text-sm text-stone-500">{item.l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section-pad border-b border-stone-200">
        <div className="container-pad">
          <Reveal>
            <p className="text-xs font-semibold text-forest-600 uppercase tracking-widest mb-2">How it works</p>
            <h2 className="font-display text-4xl sm:text-5xl text-stone-900 mb-3">Three steps to an answer</h2>
            <p className="text-stone-500 max-w-md mb-14 leading-relaxed">Grounded in actual law, not AI guesses. Every claim verified against official Acts.</p>
          </Reveal>
          <div className="grid md:grid-cols-3 gap-6">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 80}>
                <div className="relative bg-white border border-stone-200 rounded-2xl p-7 shadow-card h-full">
                  <div className="w-10 h-10 rounded-xl bg-forest-50 border border-forest-200 grid place-items-center font-display text-2xl font-semibold text-forest-700 mb-5">{s.n}</div>
                  <h3 className="font-display text-xl text-stone-900 mb-2">{s.title}</h3>
                  <p className="text-sm text-stone-500 leading-relaxed">{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* COVERAGE */}
      <section className="section-pad border-b border-stone-200 bg-white">
        <div className="container-pad">
          <Reveal>
            <p className="text-xs font-semibold text-forest-600 uppercase tracking-widest mb-2">Coverage</p>
            <h2 className="font-display text-4xl sm:text-5xl text-stone-900 mb-3">Five areas of Indian law</h2>
            <p className="text-stone-500 max-w-md mb-14 leading-relaxed">Where citizens most often face problems without legal help.</p>
          </Reveal>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {VERTICALS.map((v, i) => (
              <Reveal key={v.name} delay={i * 60}>
                <div className="bg-stone-50 border border-stone-200 rounded-2xl p-6 hover:border-forest-300 hover:shadow-lift transition-all duration-200 group">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl bg-forest-700 grid place-items-center">
                      <v.icon size={16} className="text-white" />
                    </div>
                    <span className="text-[10px] font-mono text-stone-400">{v.law}</span>
                  </div>
                  <h3 className="font-semibold text-stone-900 mb-1.5">{v.name}</h3>
                  <p className="text-sm text-stone-500 leading-relaxed">{v.desc}</p>
                </div>
              </Reveal>
            ))}
            <Reveal delay={VERTICALS.length * 60}>
              <button onClick={() => navigate("/chat")}
                className="bg-forest-700 rounded-2xl p-6 text-left w-full h-full flex flex-col justify-between min-h-[160px] hover:bg-forest-600 transition-colors cursor-pointer group">
                <p className="text-sm text-white/80 leading-relaxed">Don't know which category? Just describe your situation.</p>
                <div className="flex items-center gap-2 text-white font-semibold text-sm mt-4">
                  Ask anything <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
            </Reveal>
          </div>
        </div>
      </section>

      {/* WHY NYAYAI */}
      <section className="section-pad border-b border-stone-200">
        <div className="container-pad">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <Reveal>
              <p className="text-xs font-semibold text-forest-600 uppercase tracking-widest mb-2">Why NyayAI</p>
              <h2 className="font-display text-4xl sm:text-5xl text-stone-900 mb-5 leading-tight">
                Built on what it<br /><span className="text-forest-gradient italic">can actually verify.</span>
              </h2>
              <p className="text-stone-500 leading-relaxed mb-8">
                Most AI tools answer legal questions from training data — they confidently cite sections that say something completely different. NyayAI retrieves the actual law text first, then generates an answer from it. That's the difference.
              </p>
              <button onClick={() => navigate("/chat")}
                className="inline-flex items-center gap-2 bg-forest-700 text-white font-semibold px-6 py-3 rounded-full hover:bg-forest-600 transition-colors cursor-pointer">
                Try it yourself <ArrowRight size={14} />
              </button>
            </Reveal>
            <div className="space-y-3">
              {[
                { icon: Shield,     text: "Every answer cites the exact Act and section it comes from" },
                { icon: BookOpen,   text: "If the law doesn't cover your question, it says so — no invented provisions" },
                { icon: Scale,      text: "Runs locally — your questions are not sent to OpenAI or any cloud AI" },
                { icon: Languages,  text: "Full input and output support for English, Hindi, and Marathi" },
                { icon: FileText,   text: "Upload photos of notices, agreements, FIRs for instant analysis" },
              ].map((p, i) => (
                <Reveal key={i} delay={i * 60}>
                  <div className="flex items-start gap-3 bg-white border border-stone-200 rounded-xl px-4 py-3.5">
                    <CheckCircle2 size={16} className="text-forest-600 mt-0.5 shrink-0" />
                    <p className="text-sm text-stone-600 leading-relaxed">{p.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* SCOPE AND LIMITS */}
      <section className="section-pad border-b border-stone-200 bg-white">
        <div className="container-pad">
          <Reveal>
            <p className="text-xs font-semibold text-forest-600 uppercase tracking-widest mb-2">Before you rely on it</p>
            <h2 className="font-display text-4xl sm:text-5xl text-stone-900 mb-4">What NyayAI does, and what it doesn't</h2>
            <p className="text-stone-500 mb-12 max-w-2xl">A legal tool is only useful if you know its limits. Here are ours, stated plainly.</p>
          </Reveal>
          <div className="grid md:grid-cols-2 gap-x-10 gap-y-4">
            {HONESTY.map((item, i) => (
              <Reveal key={i} delay={i * 60}>
                <div className="flex gap-3 items-start border border-stone-200 rounded-2xl p-5 h-full shadow-card">
                  {item.good
                    ? <CheckCircle2 size={18} className="text-forest-600 shrink-0 mt-0.5" />
                    : <Shield size={18} className="text-stone-400 shrink-0 mt-0.5" />}
                  <p className="text-sm text-stone-600 leading-relaxed">{item.text}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section-pad text-center">
        <div className="max-w-2xl mx-auto px-5">
          <Reveal>
            <div className="w-14 h-14 rounded-2xl bg-forest-700 grid place-items-center mx-auto mb-6">
              <Scale size={24} className="text-white" />
            </div>
            <h2 className="font-display text-4xl sm:text-5xl text-stone-900 mb-3">
              Ready to know your rights?
            </h2>
            <p className="text-stone-500 mb-8">First three questions are free — no signup required.</p>
            <button onClick={() => navigate("/chat")}
              className="inline-flex items-center gap-2 bg-forest-700 text-white font-semibold px-9 py-4 rounded-full hover:bg-forest-600 transition-colors shadow-lift cursor-pointer text-base">
              Start asking for free <ArrowRight size={16} />
            </button>
          </Reveal>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-stone-200 py-10 bg-white">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-forest-700 grid place-items-center"><Scale size={11} className="text-white" /></div>
            <span className="font-display text-base font-semibold text-stone-700">NyayAI</span>
          </div>
          <p className="text-xs text-stone-400">NyayAI provides legal information, not legal advice. © {new Date().getFullYear()}</p>
        </div>
      </footer>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}
