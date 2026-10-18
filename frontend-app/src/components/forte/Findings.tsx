import { useState } from "react"
import { SearchCheck } from "lucide-react"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { CATEGORIES, STRENGTH, OUTSIDE_VERDICT, typeOf, type CatKey } from "@/lib/baseline"
import { IMG, TONE, fmt, tone, type Gap, type Item, type Status } from "@/lib/data"
import { ToneMark } from "./Timeline"

export const STATUS: Record<Status, { label: string; cls: string }> = {
  pending: { label: "на проверке", cls: "bg-muted text-muted-foreground" },
  confirmed: { label: "подтверждено", cls: "bg-primary text-primary-foreground" },
  rejected: { label: "отклонено", cls: "bg-muted text-muted-foreground line-through" },
}

function meta(it: Item) {
  const p = [it.iv[1] - it.iv[0] > 10 ? `${fmt(it.iv[0])}–${fmt(it.iv[1])}` : fmt(it.tc), (it.zoneMissing ? "зона не найдена" : Math.round(it.conf * 100) + "%" + (it.demoConf ? " (демо)" : "")), it.source === "vlm" ? "VLM" : "правило"]
  if (it.omission) p.push("бездействие")
  return p.join(" · ")
}

/* filter-chip по бренд-буку: белая «таблетка» с hairline, активная — заливка вином */
export function Findings({ items, gaps, sel, onSelect }: { items: Item[]; gaps: Gap[]; sel: string | null; onSelect: (id: string) => void }) {
  const [cat, setCat] = useState<CatKey | "all">("all")
  const conf = items.filter((x) => x.status === "confirmed").length
  const rej = items.filter((x) => x.status === "rejected").length
  const cats = (Object.keys(CATEGORIES) as CatKey[]).map((k) => ({ k, n: items.filter((x) => typeOf(x.tid).cat === k).length })).filter((c) => c.n > 0)
  const shown = (cat === "all" ? items : items.filter((x) => typeOf(x.tid).cat === cat)).slice().sort((a, b) => (tone(a) === "verdict" ? 0 : 1) - (tone(b) === "verdict" ? 0 : 1) || a.tc - b.tc)
  const chip = (on: boolean) => cn("flex h-8 items-center gap-1.5 rounded-full border px-3 text-[12.5px] font-medium transition-colors ease-forte",
    on ? "border-primary bg-primary text-primary-foreground" : "border-hairline bg-card text-wine-deep hover:bg-accent")
  return (
    <Card className="gap-3 py-4" data-testid="findings-card">
      <div className="flex items-baseline gap-2 px-5">
        <h2 className="text-[17px] font-semibold" data-testid="found">Находки: {items.length + gaps.length}</h2>
        <span className="text-[12.5px] text-muted-foreground">подтверждено {conf}{rej ? ` · отклонено ${rej}` : ""}</span>
      </div>
      {cats.length > 1 && (
        <div className="flex flex-wrap gap-2 px-5" data-testid="cat-filter">
          <button onClick={() => setCat("all")} className={chip(cat === "all")}>Все <span className="opacity-70">{items.length}</span></button>
          {cats.map(({ k, n }) => (
            <button key={k} data-cat={k} onClick={() => setCat(cat === k ? "all" : k)} className={chip(cat === k)}>
              <i className="size-2 rounded-full" style={{ background: cat === k ? "#fff" : CATEGORIES[k].color }} />{CATEGORIES[k].label} <span className="opacity-70">{n}</span>
            </button>
          ))}
        </div>
      )}
      {!items.length && !gaps.length ? (
        <div className="mx-5 flex items-center gap-3 rounded-xl bg-success-bg p-4" data-testid="empty-findings">
          <div className="grid size-10 place-items-center rounded-full bg-card text-success"><SearchCheck className="size-5" /></div>
          <div className="text-[13.5px]"><div className="font-semibold text-success">Ничего не найдено</div><div className="text-muted-foreground">Видео проанализировано целиком, моментов для ручной проверки нет.</div></div>
        </div>
      ) : (
        <div className="flex max-h-[420px] flex-col gap-1.5 overflow-y-auto px-3" data-testid="findings">
          {shown.map((it) => {
            const t = typeOf(it.tid), tn = tone(it)
            return (
              <button key={it.id} data-id={it.id} data-cat={t.cat} data-tone={tn} onClick={() => onSelect(it.id)}
                className={cn("group flex items-center gap-3 rounded-xl border p-2 pr-3 text-left transition ease-forte",
                  sel === it.id ? "border-sky bg-card shadow-sm ring-1 ring-sky" : "border-transparent hover:bg-muted")}>
                <span className="relative shrink-0">
                  <img src={IMG(it.frames[it.mi ?? 1].t)} alt="" className="h-[56px] w-[32px] rounded-md object-cover" />
                  <span className="absolute -bottom-1 -right-1.5"><ToneMark it={it} size={16} /></span>
                </span>
                <span className="min-w-0 flex-1">
                  <span className={cn("line-clamp-2 text-[13.5px] font-semibold leading-snug", tn === "rejected" && "line-through opacity-60")} title={it.title}>{t.name_ru}</span>
                  <span className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11.5px] text-muted-foreground">
                    <code className="font-mono text-[10.5px]" data-type-id={it.tid}>{it.tid}</code>
                    <span>·</span><span className="font-mono tabular">{meta(it)}</span>
                  </span>
                  <span className="mt-1 flex flex-wrap gap-1">
                    <span className={cn("rounded-full px-1.5 py-px text-[10.5px] font-medium", TONE[tn].bg, TONE[tn].text)} data-testid="tone-badge">{TONE[tn].label}</span>
                    {!t.count_in_verdict && <span className="rounded-full bg-warning-bg px-1.5 py-px text-[10.5px] text-warning ring-1 ring-warning-border" data-testid="outside-verdict">{OUTSIDE_VERDICT}</span>}
                    {(t.strength === "weak" || t.strength === "none") && <span className={cn("rounded-full px-1.5 py-px text-[10.5px]", STRENGTH[t.strength].cls)}>{STRENGTH[t.strength].label}</span>}
                    {it.status !== "pending" && <span className={cn("rounded-full px-1.5 py-px text-[10.5px]", STATUS[it.status].cls)}>{STATUS[it.status].label}</span>}
                  </span>
                </span>
              </button>
            )
          })}
          {cat === "all" && gaps.map((g, i) => (
            <button key={"gap" + i} data-id={"gap" + i} onClick={() => onSelect("gap" + i)}
              className={cn("flex items-center gap-3 rounded-xl border p-2 pr-3 text-left transition", sel === "gap" + i ? "border-sky bg-card ring-1 ring-sky" : "border-transparent hover:bg-muted")}>
              <span className="hatch h-[56px] w-[32px] shrink-0 rounded-md" />
              <span className="min-w-0 flex-1">
                <span className="block text-[13.5px] font-semibold">Не проанализировано</span>
                <span className="block font-mono text-[11.5px] text-muted-foreground">{fmt(g.a)}–{fmt(g.b)} · {(g.b - g.a).toFixed(1)} с</span>
                <span className={cn("mt-1 inline-block rounded-full px-1.5 py-px text-[10.5px] font-medium", TONE.manual.bg, TONE.manual.text)}>смотреть вручную</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </Card>
  )
}
