import { useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

/**
 * Tooltip que explica a "base de montagem" de um número/informação.
 * Renderiza num portal com position: fixed — não é cortado por containers
 * com overflow (listas, drawer, tabela).
 */
export default function Hint({
  text,
  children,
  className = "",
  underline = true,
}: {
  text: string;
  children: ReactNode;
  className?: string;
  underline?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  function show() {
    const r = ref.current?.getBoundingClientRect();
    if (r) setPos({ x: r.left + r.width / 2, y: r.top });
  }

  return (
    <span
      ref={ref}
      onMouseEnter={show}
      onMouseLeave={() => setPos(null)}
      className={`${underline ? "cursor-help decoration-dotted underline-offset-2 hover:underline" : "cursor-help"} ${className}`}
    >
      {children}
      {pos &&
        createPortal(
          <div
            style={{
              position: "fixed",
              left: pos.x,
              top: pos.y - 8,
              transform: "translate(-50%, -100%)",
            }}
            className="pointer-events-none z-[200] w-max max-w-xs rounded-lg bg-slate-800 px-3 py-2 text-xs leading-snug text-white shadow-xl"
          >
            <span className="mb-0.5 block text-[10px] font-bold uppercase tracking-wide text-brand-300">
              Como é calculado
            </span>
            {text}
          </div>,
          document.body
        )}
    </span>
  );
}
