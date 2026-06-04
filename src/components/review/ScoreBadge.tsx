import { useEffect, useState } from "react";

function scoreColor(score: number) {
  if (score >= 80) return "var(--success)";
  if (score >= 50) return "var(--warning)";
  return "var(--destructive)";
}

export function ScoreBadge({ score }: { score: number }) {
  const [display, setDisplay] = useState(0);
  const color = scoreColor(score);

  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const duration = 1000;
    const tick = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(eased * score));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  return (
    <div className="relative grid h-28 w-28 shrink-0 place-items-center">
      <svg className="absolute inset-0 h-full w-full -rotate-90 overflow-visible" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="16" fill="none" stroke="var(--muted)" strokeWidth="2.5" />
        <circle
          cx="18"
          cy="18"
          r="16"
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={`${display} 100`}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <div className="text-center">
        <span className="text-3xl font-extrabold" style={{ color }}>
          {display}
        </span>
        <p className="text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
          / 100
        </p>
      </div>
    </div>
  );
}
