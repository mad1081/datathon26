import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import { CATEGORIES, SESSIONS, BASELINE, SEVERITY, STEPS, TAXONOMY, type CatKey } from "@/lib/baseline"
import type { Item } from "@/lib/data"
import { ClauseChip, CodeBadge, Unverified } from "./Clause"

const sessOf = (step: string) => SESSIONS.filter((s) => BASELINE[s.key].includes(step)).map((s) => s.label).join(" / ")

/* справочник типов: код → категория, критичность, шаг эталона, пункт, сигнал детектора */
export function Taxonomy({ open, onOpen, items }: { open: boolean; onOpen: (o: boolean) => void; items: Item[] }) {
  const cats = Object.keys(CATEGORIES) as CatKey[]
  return (
    <Sheet open={open} onOpenChange={onOpen}>
      <SheetContent side="right" className="gap-0 overflow-y-auto data-[side=right]:w-[560px] data-[side=right]:sm:max-w-[560px]" data-testid="taxonomy">
        <SheetHeader className="border-b pb-3">
          <SheetTitle>Типы нарушений</SheetTitle>
          <SheetDescription className="text-[12px]">
            Нарушение = отклонение от шага эталона. У каждого типа — код (идёт в <code className="font-mono">violations[].type</code>), категория, критичность, шаг эталона и пункт Правил.
          </SheetDescription>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {cats.map((k) => <span key={k} className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]"><i className="size-2 rounded-full" style={{ background: CATEGORIES[k].color }} />{CATEGORIES[k].label}</span>)}
          </div>
        </SheetHeader>
        <div className="space-y-4 p-4">
          {cats.map((k) => {
            const list = TAXONOMY.filter((t) => t.cat === k)
            return (
              <section key={k}>
                <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em]" style={{ color: CATEGORIES[k].color }}>
                  <i className="size-2 rounded-full" style={{ background: CATEGORIES[k].color }} />{CATEGORIES[k].label}
                </div>
                <div className="space-y-2">
                  {list.map((t) => {
                    const n = items.filter((x) => x.code === t.code).length
                    return (
                      <div key={t.code} className="rounded-lg border bg-card p-2.5" data-type={t.code} style={{ borderLeft: `3px solid ${CATEGORIES[k].color}` }}>
                        <div className="flex items-center gap-2">
                          <CodeBadge code={t.code} />
                          <span className="min-w-0 flex-1 text-[13px] font-semibold leading-snug">{t.title}</span>
                          <span className={cn("shrink-0 rounded-full px-1.5 py-px text-[10px]", SEVERITY[t.severity].cls)}>{SEVERITY[t.severity].label}</span>
                          {n > 0 && <span className="shrink-0 rounded-full bg-accent px-1.5 py-px text-[10px] font-semibold text-primary">в видео: {n}</span>}
                        </div>
                        <div className="mt-1.5 grid grid-cols-[92px_minmax(0,1fr)] gap-x-2 gap-y-1 text-[11.5px]">
                          <span className="text-muted-foreground">пункт</span>
                          <span className="flex flex-wrap items-center gap-1">{t.cites.length ? t.cites.map((c) => <ClauseChip key={c} k={c} />) : <><span className="text-muted-foreground">прямого пункта нет · производный</span><Unverified text="Производный признак детектора, прямой нормы нет" /></>}</span>
                          <span className="text-muted-foreground">шаг эталона</span>
                          <span>{t.steps.map((s) => <span key={s} className="block leading-snug">{STEPS[s].title} <span className="text-muted-foreground">({sessOf(s)})</span></span>)}</span>
                          <span className="text-muted-foreground">сигнал</span>
                          <span className="leading-snug">{t.detector}</span>
                        </div>
                        {t.caveat && <div className="mt-1.5 rounded-md bg-warning-bg px-2 py-1 text-[11px] leading-snug text-warning">{t.caveat}</div>}
                      </div>
                    )
                  })}
                </div>
              </section>
            )
          })}
          <p className="text-[11px] text-muted-foreground">Критичное — прямой запрет Правил, влияет на <code className="font-mono">verdict</code>. Среднее — нужен контекст (исключения, тип телефона, производный признак): чаще уходит в «проверить вручную».</p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
