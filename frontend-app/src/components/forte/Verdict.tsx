import { CircleCheck, OctagonAlert, TriangleAlert, ChevronRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { fmt, plural } from "@/lib/data"

type Props = { v: number; r: number; g: number; dur: number; src: "real" | "demo"; onReview: () => void }

export function Verdict({ v, r, g, dur, src, onReview }: Props) {
  const n = r + g
  const red = v > 0
  return (
    <div className="space-y-2.5">
      {src === "real"
        ? <Badge variant="outline" className="border-success/30 bg-success-bg text-success">● реальное видео · уверенность — демо-значение</Badge>
        : <Badge variant="outline" className="border-dashed border-primary/40 bg-accent text-primary">демо-данные, не результат модели</Badge>}
      <div data-testid="verdict" className={cn("flex items-start gap-3 rounded-xl border p-3.5", red ? "border-destructive/30 bg-danger-bg" : "border-success/30 bg-success-bg")}>
        <div className={cn("grid size-9 shrink-0 place-items-center rounded-full text-white", red ? "bg-destructive" : "bg-success")}>
          {red ? <OctagonAlert className="size-5" /> : <CircleCheck className="size-5" />}
        </div>
        <div className="min-w-0">
          <div className={cn("text-[16px] font-bold leading-tight", red ? "text-destructive" : "text-success")} data-testid="verdict-title">
            {red ? "Обнаружены признаки возможных нарушений" : "Нарушений не обнаружено"}
          </div>
          <div className="mt-1 text-[12.5px] text-muted-foreground">
            {red ? `${v} ${plural(v, "нарушение", "нарушения", "нарушений")} выше порога правил` : n ? "Нарушений выше порога правил нет" : `Видео ${fmt(dur)} проанализировано целиком`}
          </div>
          <code className="mt-1.5 inline-block rounded bg-card/70 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">"verdict": "{red ? "violation" : "no_violation"}"</code>
        </div>
      </div>
      {n > 0 && (
        <button onClick={onReview} data-testid="review-note"
          className="flex w-full items-center gap-2.5 rounded-lg border border-warning-border bg-warning-bg px-3 py-2 text-left text-warning transition hover:brightness-[0.98]">
          <TriangleAlert className="size-4 shrink-0" />
          <span className="min-w-0 flex-1">
            <span className="block text-[13px] font-semibold">{n} {plural(n, "момент", "момента", "моментов")} проверить вручную</span>
            <span className="block text-[11.5px] opacity-80">{[r ? `${r} ниже порога / VLM` : "", g ? `${g} не ${plural(g, "проанализирован", "проанализированы", "проанализированы")}` : ""].filter(Boolean).join(" · ")}</span>
          </span>
          <ChevronRight className="size-4" />
        </button>
      )}
    </div>
  )
}
