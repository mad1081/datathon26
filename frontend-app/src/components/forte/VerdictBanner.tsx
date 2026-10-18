import { OctagonAlert, CircleCheck, TriangleAlert, ChevronRight, ListChecks } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fmt, plural } from "@/lib/data"

type Props = {
  v: number; r: number; g: number; dur: number; src: "real" | "demo"; file: string; session: string
  comp: { ok: number; total: number } | null
  onFirstViolation: () => void; onReview: () => void
}

/* Главный вердикт: бинарный (violation | no_violation); ручная проверка — отдельной плашкой, не третий вердикт */
export function VerdictBanner({ v, r, g, dur, src, file, session, comp, onFirstViolation, onReview }: Props) {
  const red = v > 0
  const n = r + g
  const pct = comp && comp.total ? Math.round((comp.ok / comp.total) * 100) : null
  return (
    <section data-testid="verdict"
      className={cn("fade-in relative overflow-hidden rounded-2xl p-6 max-[1360px]:p-5", red ? "text-white" : "border border-success/25 bg-card")}
      style={red ? { background: "var(--grad-hero)", boxShadow: "rgba(0,0,0,0.1) 0 4px 8px" } : undefined}>
      {!red && <div className="pointer-events-none absolute inset-y-0 left-0 w-1.5 bg-success" />}
      <div className="flex items-center gap-6 max-[1360px]:gap-4">
        <div className={cn("grid size-16 shrink-0 place-items-center rounded-full max-[1360px]:size-14", red ? "bg-white text-destructive" : "bg-success-bg text-success")}>
          {red ? <OctagonAlert className="size-8" /> : <CircleCheck className="size-8" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className={cn("flex flex-wrap items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.14em]", red ? "text-white/80" : "text-slate")}>
            <span>Вердикт</span>
            <code className={cn("rounded-md px-1.5 py-0.5 font-mono text-[11px] normal-case tracking-normal", red ? "bg-white/15 text-white" : "bg-muted text-muted-foreground")}>"verdict": "{red ? "violation" : "no_violation"}"</code>
            <span className={cn("rounded-full px-2 py-0.5 text-[10.5px] normal-case tracking-normal", red ? "bg-white text-primary" : src === "real" ? "bg-success-bg text-success" : "bg-accent text-primary")} data-testid="src-badge">
              {src === "real" ? "реальное видео · уверенность — демо" : "демо-данные, не результат модели"}
            </span>
          </div>
          <h1 className={cn("mt-1.5 text-[32px] font-bold leading-[1.15] tracking-[-0.01em] max-[1360px]:text-[28px]", red ? "!text-white" : "")} data-testid="verdict-title">
            {red ? "Есть признаки возможных нарушений" : "Нарушений не обнаружено"}
          </h1>
          <div className={cn("mt-1.5 text-[14px]", red ? "text-white/85" : "text-muted-foreground")}>
            <span className="font-mono">{file}</span> · {fmt(dur)} · сессия: {session}
          </div>
        </div>

        <div className="flex shrink-0 items-stretch gap-3" data-testid="verdict-stats">
          <Stat red={red} tone="verdict" value={v} label={plural(v, "нарушение", "нарушения", "нарушений") + " в вердикте"} onClick={v ? onFirstViolation : undefined} testid="stat-verdict" />
          <Stat red={red} tone="manual" value={n} label={"проверить вручную"} sub={[r ? `${r} ниже порога / вне вердикта` : "", g ? `${g} не проанализ.` : ""].filter(Boolean).join(" · ")} onClick={n ? onReview : undefined} testid="review-note" />
          {comp && pct !== null && (
            <div className={cn("flex w-[170px] flex-col justify-between rounded-xl p-3.5 max-[1360px]:w-[150px]", red ? "bg-white text-[#1D1D1D] dark:bg-card dark:text-foreground" : "bg-muted")}>
              <div className="flex items-center gap-1.5 text-[12px] font-medium text-slate"><ListChecks className="size-3.5" />Эталон процедуры</div>
              <div className="text-[26px] font-bold leading-none text-primary tabular dark:text-foreground">{comp.ok}<span className="text-[16px] font-semibold text-muted-foreground">/{comp.total}</span></div>
              <div className="h-1.5 overflow-hidden rounded-full bg-surface-gray"><div className="h-full rounded-full bg-sky transition-all" style={{ width: `${pct}%` }} /></div>
            </div>
          )}
        </div>
      </div>
      {red && v > 0 && (
        <div className="mt-4 flex gap-2 pl-[88px] max-[1360px]:pl-[72px]">
          <Button variant="inverse" size="lg" onClick={onFirstViolation} data-testid="goto-first">К первому нарушению<ChevronRight /></Button>
          {n > 0 && <Button variant="inverse" size="lg" onClick={onReview}><TriangleAlert className="text-[#B07A00]" />Ручная проверка: {n}</Button>}
        </div>
      )}
    </section>
  )
}

function Stat({ red, tone, value, label, sub, onClick, testid }: { red: boolean; tone: "verdict" | "manual"; value: number; label: string; sub?: string; onClick?: () => void; testid: string }) {
  const El = onClick ? "button" : "div"
  const zero = value === 0
  return (
    <El onClick={onClick} data-testid={testid}
      className={cn("flex w-[150px] flex-col justify-between gap-1 rounded-xl p-3.5 text-left transition ease-forte max-[1360px]:w-[136px]",
        red ? "bg-white text-[#1D1D1D] dark:bg-card dark:text-foreground" : "bg-muted", onClick && "hover:-translate-y-0.5 hover:shadow-md")}>
      <div className="flex items-center gap-1.5">
        <span className={cn("grid size-5 place-items-center rounded-full text-[11px] font-bold text-white", zero ? "bg-muted-foreground/40" : tone === "verdict" ? "bg-destructive" : "bg-amber")}>{tone === "verdict" ? "!" : "?"}</span>
        <span className={cn("text-[28px] font-bold leading-none tabular", zero ? "text-muted-foreground" : tone === "verdict" ? "text-destructive" : "text-warning")}>{value}</span>
      </div>
      <div className="text-[12.5px] font-medium leading-snug">{label}</div>
      {sub && <div className="text-[11px] leading-snug text-muted-foreground">{sub}</div>}
    </El>
  )
}
