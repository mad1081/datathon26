import { cn } from "@/lib/utils"
import { ZONES, type ZoneKey } from "@/lib/data"

/* Полупрозрачные зоны поверх кадра. Координаты нормированы 0..1 к кадру 464×848,
   контейнер имеет тот же aspect-ratio, поэтому совпадает с object-contain/cover. */
export function ZoneOverlay({ found, light, className }: { found: ZoneKey[]; light?: boolean; className?: string }) {
  return (
    <div className={cn("pointer-events-none absolute inset-0", className)} data-testid={light ? undefined : "zones"}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
        {ZONES.map((z) => {
          const ok = found.includes(z.key)
          return (
            <polygon key={z.key} points={z.polygon.map(([x, y]) => `${x * 100},${y * 100}`).join(" ")}
              fill={ok ? z.color : "transparent"} fillOpacity={light ? 0.14 : 0.24}
              stroke={z.color} strokeOpacity={light ? 0.55 : 0.95} strokeWidth={light ? 1 : 1.6}
              strokeDasharray={ok ? undefined : "3 2.5"} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
          )
        })}
      </svg>
      {!light && ZONES.map((z) => {
        const ok = found.includes(z.key)
        const xs = z.polygon.map((p) => p[0]), ys = z.polygon.map((p) => p[1])
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2, top = Math.min(...ys)
        return (
          <span key={z.key} data-zone={z.key}
            className="absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded px-1 py-px text-[9.5px] font-semibold leading-tight text-white shadow-sm"
            style={{ left: `${Math.min(Math.max(cx, 0.12), 0.86) * 100}%`, top: `calc(${top * 100}% - 2px)`, background: ok ? z.color : "rgba(0,0,0,.65)", outline: ok ? undefined : `1px dashed ${z.color}` }}>
            {z.short}{!ok && " · не найдена"}
          </span>
        )
      })}
    </div>
  )
}
