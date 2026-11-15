const CITATIONS = [
  "Section 6 · RTI Act 2005", "Section 19 · RTI Act 2005",
  "Section 106 · Maharashtra Rent Control Act", "Section 2(7) · Consumer Protection Act 2019",
  "Section 35 · Consumer Protection Act 2019", "Section 13 · Hindu Marriage Act 1955",
  "Section 144 · BNSS 2023", "Section 12 · Domestic Violence Act 2005",
  "Section 318 · BNS 2023", "Section 23 · Model Tenancy Act 2021",
];

export default function CitationMarquee() {
  const items = [...CITATIONS, ...CITATIONS];
  return (
    <div className="relative overflow-hidden py-3 select-none" aria-hidden="true">
      <div className="absolute inset-y-0 left-0 w-16 sm:w-32 bg-gradient-to-r from-ink to-transparent z-10" />
      <div className="absolute inset-y-0 right-0 w-16 sm:w-32 bg-gradient-to-l from-ink to-transparent z-10" />
      <div className="marquee-track">
        {items.map((c, i) => (
          <span
            key={i}
            className="font-mono text-xs text-brass-300/35 px-6 whitespace-nowrap"
          >
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
