import { useState } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { CATEGORIES, STRENGTH, OUTSIDE_VERDICT, typeOf, type CatKey } from "@/lib/baseline"
import { IMG, fmt, type Gap, type Item, type Status } from "@/lib/data"

export const STATUS: Record<Status, { label: string; cls: string }> = {
  pending: { label: "на проверке", cls: "bg-muted text-muted-foreground" },
  confirmed: { label: "подтверждено", cls: "bg-plum text-white dark:bg-primary" },
  rejected: { label: "отклонено", cls: "bg-muted text-muted-foreground line-through" },
}

function meta(it: Item) {
  const p = [it.iv[1] - it.iv[0] > 10 ? `${fmt(it.iv[0])}–${fmt(it.iv[1])}` : fmt(it.tc), (it.zoneMissing ? "зона не найдена" : Math.round(it.conf * 100) + "%" + (it.demoConf ? " (демо)" : "")), it.source === "vlm" ? "VLM" : "правило"]
  if (it.omission) p.push("бездействие")
  if (it.kind === "observation") p.push(it.source === "vlm" ? "ниже порога" : !typeOf(it.tid).citations.length ? "нормы нет" : it.rule ? "ниже порога" : "вручную")
  return p.join(" · ")
}

export function Findings({ items, gaps, sel, onSelect }: { items: Item[]; gaps: Gap[]; sel: string | null; onSelect: (id: string) => void }) {
  const [cat, setCat] = useState<CatKey | "all">("all")
  const conf = items.filter((x) => x.status === "confirmed").length
  const rej = items.filter((x) => x.status === "rejected").length
  const cats = (Object.keys(CATEGORIES) as CatKey[]).map((k) => ({ k, n: items.filter((x) => typeOf(x.tid).cat === k).length })).filter((c) => c.n > 0)
  const shown = cat === "all" ? items : items.filter((x) => typeOf(x.tid).cat === cat)
  return (
    <div>
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-[16px] font-bold" data-testid="found">Найдено: {items.length}</span>
        <span className="text-xs text-muted-foreground">подтверждено {conf}{rej ? ` · отклонено ${rej}` : ""}</span>
      </div>
      {cats.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1" data-testid="cat-filter">
          <button onClick={() => setCat("all")} className={cn("rounded-full border px-2 py-0.5 text-[11px]", cat === "all" ? "border-foreground bg-foreground text-background" : "hover:bg-muted")}>все {items.length}</button>
          {cats.map(({ k, n }) => {
            const c = CATEGORIES[k], on = cat === k
            return (
              <button key={k} data-cat={k} onClick={() => setCat(on ? "all" : k)}
                className={cn("flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition", !on && "hover:bg-muted")}
                style={on ? { background: c.color, borderColor: c.color, color: "#fff" } : { borderColor: c.color + "66" }}>
                <i className="size-2 rounded-full" style={{ background: on ? "#fff" : c.color }} />{c.label} <span className="opacity-70">{n}</span>
              </button>
            )
          })}
        </div>
      )}
      {!items.length && !gaps.length ? (
        <div className="rounded-lg bg-muted p-3.5 text-[13px] text-muted-foreground">Ничего не найдено. Видео проанализировано целиком, моментов для ручной проверки нет.</div>
      ) : (
        <ScrollArea className="max-h-[330px] pr-2 [&>[data-slot=scroll-area-viewport]]:max-h-[330px] [&>[data-slot=scroll-area-viewport]>div]:!block">
          <div className="flex flex-col gap-1.5" data-testid="findings">
            {shown.map((it) => {
              const t = typeOf(it.tid)
              return (
                <button key={it.id} data-id={it.id} data-cat={t.cat} onClick={() => onSelect(it.id)}
                  className={cn("flex items-center gap-2.5 rounded-lg border border-transparent bg-muted/70 p-1.5 pr-2.5 text-left transition hover:bg-muted",
                    sel === it.id && "border-primary bg-card shadow-sm")}>
                  <span className="relative shrink-0">
                    <img src={IMG(it.frames[it.mi ?? 1].t)} alt="" className="h-[52px] w-[30px] rounded object-cover" />
                    <span className="absolute inset-y-1 -left-1 w-1 rounded-full" style={{ background: it.color }} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className={cn("line-clamp-2 text-[13px] font-semibold leading-snug", it.status === "rejected" && "line-through opacity-60")} title={it.title}>{t.name_ru}</span>
                    <span className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-muted-foreground"><code className="font-mono text-[10px]" style={{ color: it.color }} data-type-id={it.tid}>{it.tid}</code> · {meta(it)}{!t.count_in_verdict && <span className="ml-1 rounded bg-warning-bg px-1 text-[9.5px] text-warning ring-1 ring-warning-border" data-testid="outside-verdict">{OUTSIDE_VERDICT}</span>}{(t.strength === "weak" || t.strength === "none") && <span className={cn("ml-1 rounded px-1 text-[9.5px]", STRENGTH[t.strength].cls)}>{STRENGTH[t.strength].label}</span>}</span>
                  </span>
                  <Badge className={cn("shrink-0 rounded-full text-[10.5px]", STATUS[it.status].cls)}>{STATUS[it.status].label}</Badge>
                </button>
              )
            })}
            {cat === "all" && gaps.map((g, i) => (
              <button key={"gap" + i} data-id={"gap" + i} onClick={() => onSelect("gap" + i)}
                className={cn("flex items-center gap-2.5 rounded-lg border border-transparent bg-muted/70 p-1.5 pr-2.5 text-left hover:bg-muted", sel === "gap" + i && "border-primary bg-card shadow-sm")}>
                <span className="hatch h-[52px] w-[30px] shrink-0 rounded" />
                <span className="min-w-0 flex-1">
                  <span className="block text-[13.5px] font-semibold">Не проанализировано</span>
                  <span className="block text-[11.5px] text-muted-foreground">{fmt(g.a)}–{fmt(g.b)} · {(g.b - g.a).toFixed(1)} с</span>
                </span>
                <Badge variant="outline" className="shrink-0 rounded-full text-[10.5px]">смотреть вручную</Badge>
              </button>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
