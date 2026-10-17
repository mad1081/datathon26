import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import { CATEGORIES, SESSIONS, BASELINE, STEPS, STRENGTH, RULES, typeOf, type CatKey } from "@/lib/baseline"
import type { Item } from "@/lib/data"
import { RuleCiteChip } from "./Clause"

const sessOf = (step: string) => SESSIONS.filter((s) => BASELINE[s.key].includes(step)).map((s) => s.label).join(" / ")

/* справочник типов = research/rules.json: name_ru, ключ, сила основания, в вердикт, нормы самого правила, примечание */
export function Taxonomy({ open, onOpen, items }: { open: boolean; onOpen: (o: boolean) => void; items: Item[] }) {
  const cats = Object.keys(CATEGORIES) as CatKey[]
  return (
    <Sheet open={open} onOpenChange={onOpen}>
      <SheetContent side="right" className="gap-0 overflow-y-auto data-[side=right]:w-[600px] data-[side=right]:sm:max-w-[600px]" data-testid="taxonomy">
        <SheetHeader className="border-b pb-3">
          <SheetTitle>Типы нарушений <span className="ml-1 font-mono text-[12px] font-normal text-muted-foreground">research/rules.json · {RULES.length}</span></SheetTitle>
          <SheetDescription className="text-[12px]">
            В ответе API: <code className="font-mono">type</code> = русское название (<code className="font-mono">name_ru</code>), <code className="font-mono">type_id</code> = ключ. Нормы, сила основания и «в вердикт» — из rules.json, без дописок. Группы — только для фильтра в интерфейсе.
          </SheetDescription>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {(Object.keys(STRENGTH) as (keyof typeof STRENGTH)[]).map((k) => <span key={k} className={cn("rounded-full px-2 py-0.5 text-[10.5px]", STRENGTH[k].cls)}>{STRENGTH[k].label}</span>)}
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10.5px] text-muted-foreground ring-1 ring-border">вне вердикта</span>
          </div>
        </SheetHeader>
        <div className="space-y-4 p-4">
          {cats.map((k) => {
            const list = RULES.filter((r) => typeOf(r.id).cat === k)
            if (!list.length) return null
            return (
              <section key={k}>
                <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em]" style={{ color: CATEGORIES[k].color }}>
                  <i className="size-2 rounded-full" style={{ background: CATEGORIES[k].color }} />{CATEGORIES[k].label}
                </div>
                <div className="space-y-2">
                  {list.map((r) => {
                    const t = typeOf(r.id)
                    const n = items.filter((x) => x.tid === r.id).length
                    return (
                      <div key={r.id} className={cn("rounded-lg border bg-card p-2.5", !r.count_in_verdict && "bg-muted/40")} data-type={r.id} style={{ borderLeft: `3px solid ${CATEGORIES[k].color}` }}>
                        <div className="flex items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="text-[13px] font-semibold leading-snug">{r.name_ru}</div>
                            <div className="font-mono text-[10.5px] text-muted-foreground">{r.id}</div>
                          </div>
                          <div className="flex shrink-0 flex-wrap justify-end gap-1">
                            <span className={cn("rounded-full px-1.5 py-px text-[10px]", STRENGTH[r.strength].cls)}>{STRENGTH[r.strength].label}</span>
                            {!r.count_in_verdict && <span className="rounded-full bg-muted px-1.5 py-px text-[10px] text-muted-foreground ring-1 ring-border" data-testid="excluded">вне вердикта</span>}
                            {n > 0 && <span className="rounded-full bg-accent px-1.5 py-px text-[10px] font-semibold text-primary">в видео: {n}</span>}
                          </div>
                        </div>
                        <div className="mt-1.5 grid grid-cols-[92px_minmax(0,1fr)] gap-x-2 gap-y-1 text-[11.5px]">
                          <span className="text-muted-foreground">нормы</span>
                          <span className="flex flex-wrap items-center gap-1">{r.citations.length ? r.citations.map((c, i) => <RuleCiteChip key={i} c={c} />) : <span className="rounded bg-danger-bg px-1 text-[10.5px] text-destructive">нет нормы в актах РК</span>}
                            {!r.has_solid_clause && r.citations.length > 0 && <span className="text-[10.5px] text-warning">· нет твёрдой нормы</span>}</span>
                          <span className="text-muted-foreground">шаг эталона</span>
                          <span>{t.steps.length ? t.steps.map((s) => <span key={s} className="block leading-snug">{STEPS[s].title} <span className="text-muted-foreground">({sessOf(s)})</span></span>) : <span className="text-muted-foreground">вне эталона</span>}</span>
                          <span className="text-muted-foreground">порог</span>
                          <span className="font-mono">{r.threshold}</span>
                          {r.visual_criteria && <><span className="text-muted-foreground">что видно</span><span className="leading-snug">{r.visual_criteria}</span></>}
                        </div>
                        {r.note && <div className="mt-1.5 rounded-md bg-warning-bg px-2 py-1 text-[11px] leading-snug text-warning">{r.note}</div>}
                      </div>
                    )
                  })}
                </div>
              </section>
            )
          })}
        </div>
      </SheetContent>
    </Sheet>
  )
}
