import { useMemo } from "react";

const TOKENS = [
  "{", "}", "=>", "//", "const", "null", "<div>", "import", "async", "await",
  "function", "return", "if", "else", "for", "while", "class", "extends",
  "===", "!==", "&&", "||", "...", "[]", "()", "=", ";", ":", ",", ".",
  "type", "interface", "enum", "let", "var", "true", "false", "undefined",
  "try", "catch", "finally", "throw", "new", "this", "super", "yield",
  "from", "export", "default", "as", "typeof", "instanceof", "void",
  "<>", "</>", "{", "}", "[", "]", "|>", "??", "?.", "++", "--",
  "<=", ">=", "<<", ">>", "**", "%=", "+=", "-="
];

interface FloatingToken {
  text: string;
  left: number;
  top: number;
  size: number;
  color: "purple" | "pink";
  opacity: number;
  animDuration: number;
  animDelay: number;
  animName: "drift-up-fade" | "drift-up-fade-slow" | "pulse-fade";
}

function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

export function FloatingCodeBackground() {
  const tokens = useMemo(() => {
    const rand = seededRandom(42);
    const result: FloatingToken[] = [];
    const count = 48;

    for (let i = 0; i < count; i++) {
      const topRaw = rand();
      // Larger characters cluster near bottom (top 60-95%), smaller everywhere
      const top = topRaw < 0.4
        ? 5 + topRaw / 0.4 * 35  // upper area: 5-40%
        : 40 + (topRaw - 0.4) / 0.6 * 55; // lower area: 40-95%

      const size = top > 60
        ? 14 + rand() * 18  // larger near bottom
        : 10 + rand() * 12;

      const opacity = 0.04 + rand() * 0.06; // 4-10% opacity

      const anims: FloatingToken["animName"][] = [
        "drift-up-fade",
        "drift-up-fade-slow",
        "pulse-fade",
      ];

      result.push({
        text: TOKENS[Math.floor(rand() * TOKENS.length)],
        left: rand() * 100,
        top,
        size,
        color: rand() > 0.5 ? "purple" : "pink",
        opacity,
        animDuration: 8 + rand() * 14,
        animDelay: rand() * 10,
        animName: anims[Math.floor(rand() * anims.length)],
      });
    }

    return result;
  }, []);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
      style={{ fontFamily: "var(--font-mono)" }}
    >
      {tokens.map((t, i) => (
        <span
          key={i}
          className="absolute select-none whitespace-nowrap will-change-transform"
          style={{
            left: `${t.left}%`,
            top: `${t.top}%`,
            fontSize: `${t.size}px`,
            color: t.color === "purple" ? "#8B5CF6" : "#EC4899",
            opacity: t.opacity,
            animation: `${t.animName} ${t.animDuration}s ease-in-out ${t.animDelay}s infinite both`,
          }}
        >
          {t.text}
        </span>
      ))}
    </div>
  );
}
