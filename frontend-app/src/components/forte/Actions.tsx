import { AlertTriangle, Footprints } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { fmt } from "@/lib/data"
import type { ApiResult } from "@/lib/api"
import { currentRow, violationRows } from "@/lib/timeline"

type Props = { result: ApiResult | null; ph: number; onSeek: (t: number) => void }

/* «Действия кассира»: хронология и сценарий из ответа сервиса (поля timeline, scenario, violations) */
export function Actions({ result, ph, onSeek }: Props) {
  if (!result) {
    return (
      <Card className="px-4 py-3 text-[12.5px] text-muted-foreground" data-testid="actions-empty">
        Хронология действий приходит от сервиса. Загрузите видео на экране «Загрузка» в режиме «Сервер» — здесь появятся сценарий и действия кассира по секундам.
      </Card>
    )
  }
  const timeline = result.timeline ?? []
  const bad = violationRows(timeline, result.violations)
  const now = currentRow(timeline, ph)
  return (
    <Card className="gap-0 py-0" data-testid="actions">
      <div className="flex items-center gap-2 px-4 pt-3">
        <Footprints className="size-4 text-primary" />
        <span className="text-[17px] font-semibold">Действия кассира</span>
        {result.scenario && <span className="text-[12px] text-muted-foreground">· {result.scenario}</span>}
      </div>

      {result.violations.length > 0 && (
        <div className="flex flex-col gap-1 px-4 pt-2">
          {result.violations.map((v, i) => (
            <button key={i} onClick={() => onSeek(v.timecode_sec)}
              className="flex items-start gap-2 rounded-md bg-danger-bg/60 px-2 py-1.5 text-left text-[12.5px] hover:brightness-95">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-destructive" />
              <span className="font-medium text-destructive">{v.type}</span>
              <span className="ml-auto shrink-0 font-mono text-[11px] tabular text-destructive">{fmt(v.timecode_sec)}</span>
            </button>
          ))}
        </div>
      )}

      <CardContent className="px-2 pb-2 pt-2">
        {timeline.length === 0 ? (
          <div className="px-2 py-1.5 text-[12.5px] text-muted-foreground">Сервис не вернул хронологию для этого видео.</div>
        ) : (
          <ol>
            {timeline.map((e, i) => (
              <li key={i}>
                <button onClick={() => onSeek(e.t)} data-now={i === now} data-violation={bad.has(i)}
                  className={cn("group flex w-full items-start gap-3 rounded-md px-2 py-1.5 text-left hover:bg-muted/70",
                    bad.has(i) && "bg-danger-bg/60", i === now && "ring-1 ring-primary/40")}>
                  <span className={cn("mt-px w-[64px] shrink-0 whitespace-nowrap font-mono text-[11px] tabular text-muted-foreground group-hover:text-primary", i === now && "text-primary")}>
                    {fmt(e.t)}
                  </span>
                  <span className={cn("text-[12.5px] leading-snug", bad.has(i) && "font-medium text-destructive")}>{e.event}</span>
                  {bad.has(i) && <span className="ml-auto shrink-0 rounded bg-destructive px-1.5 text-[10.5px] font-medium text-white">нарушение</span>}
                </button>
              </li>
            ))}
          </ol>
        )}
        <div className="px-2 pt-1 text-[10.5px] text-muted-foreground">Хронология составлена моделью по кадрам — сверяйте с видео. Клик по строке — перемотка к моменту.</div>
      </CardContent>
    </Card>
  )
}
