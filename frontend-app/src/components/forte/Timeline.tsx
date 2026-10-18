import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronDown, Eye } from "lucide-react"
import { Card } from "@/components/ui/card"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"
import { TRACKS, CASH_STATES, ZONE_BY_KEY, TONE, fmt, IMG, nearestFrame, phaseStatus, tone, type Item, type Phase, type Scenario, type Seg, type TrackKey } from "@/lib/data"
import { SESSION_BY_KEY, typeOf } from "@/lib/baseline"

type Props = { S: Scenario; items: Item[]; sel: string | null; ph: number; onSelect: (id: string) => void; onSeek: (t: number) => void }

const MAIN: TrackKey[] = ["client_at_window", "cashier_at_desk", "cash_location"]
const EXTRA: TrackKey[] = ["counting", "second_employee", "phone", "document_card"]

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [w, setW] = useState(700)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w] as const
}

const chipW = (it: Item) => 34 + it.short.length * 6.6 + 44
const tsec = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`

/* Знак находки: круг «!» — в вердикте, ромб «?» — ручная проверка (включая count_in_verdict:false), «×» — отклонено. Цвет — только по тону, не по категории. */
export function ToneMark({ it, size = 18 }: { it: Item; size?: number }) {
  const tn = tone(it)
  return (
    <span className={cn("grid shrink-0 place-items-center font-bold text-white", tn === "manual" ? "rounded-[5px] rotate-45" : "rounded-full")}
      style={{ width: tn === "manual" ? size - 3 : size, height: tn === "manual" ? size - 3 : size, background: TONE[tn].color, fontSize: size * 0.58 }} data-tone={tn}>
      <span className={tn === "manual" ? "-rotate-45" : ""}>{tn === "verdict" ? "!" : tn === "manual" ? "?" : "×"}</span>
    </span>
  )
}

export function Timeline({ S, items, sel, ph, onSelect, onSeek }: Props) {
  const [areaRef, W] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  const [all, setAll] = useState(location.hash.includes("tracks"))
  const pct = (t: number) => `${(Math.min(Math.max(t, 0), S.dur) / S.dur) * 100}%`

  const placed = useMemo(() => {
    const lanes: number[] = []
    return [...items].sort((a, b) => a.tc - b.tc).map((it) => {
      const w = chipW(it), x0 = (it.tc / S.dur) * W, flip = x0 + w > W, left = flip ? x0 - w : x0
      let lane = lanes.findIndex((end) => end + 6 < left)
      if (lane < 0) { lanes.push(0); lane = lanes.length - 1 }
      lanes[lane] = left + w
      return { it, lane, flip }
    })
  }, [items, S.dur, W])
  const laneCount = Math.max(1, ...placed.map((p) => p.lane + 1))
  const ticks = Array.from({ length: Math.floor(S.dur) + 1 }, (_, i) => i)
  const seekFromEvent = (e: React.MouseEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const t = ((e.clientX - r.left) / r.width) * S.dur
    const gi = S.gaps.findIndex((g) => t >= g.a && t <= g.b)
    if (gi >= 0) onSelect("gap" + gi)
    else onSeek(t)
  }
  const rows = all ? [...MAIN, ...EXTRA] : MAIN
  const nV = items.filter((x) => tone(x) === "verdict").length, nM = items.filter((x) => tone(x) === "manual").length

  return (
    <Card className="relative gap-3 py-4" data-testid="timeline">
      <div className="flex items-center gap-3 px-5">
        <h2 className="text-[17px] font-semibold">Таймлайн</h2>
        <span className="flex items-center gap-2.5 whitespace-nowrap text-[12.5px] text-muted-foreground">
          <span className="flex items-center gap-1"><i className="size-2.5 rounded-full bg-destructive" />{nV} в вердикте</span>
          <span className="flex items-center gap-1"><i className="size-2.5 rotate-45 rounded-[2px] bg-amber" />{nM} вручную</span>
        </span>
        <span className="ml-auto whitespace-nowrap font-mono text-[13px] text-muted-foreground tabular" data-testid="tltime">{fmt(ph)} / {fmt(S.dur)}</span>
        <button onClick={() => setAll(!all)} data-testid="tracks-toggle" aria-expanded={all}
          className="flex h-8 shrink-0 items-center gap-1 whitespace-nowrap rounded-full border px-3 text-[12.5px] font-medium text-primary transition-colors hover:bg-accent dark:text-foreground">
          {all ? "Свернуть" : `Все дорожки +${EXTRA.length + 1}`}<ChevronDown className={cn("size-3.5 transition-transform", all && "rotate-180")} />
        </button>
      </div>
      <div className="px-5">
        <div className="grid grid-cols-[132px_minmax(0,1fr)] gap-y-2 max-[1360px]:grid-cols-[112px_minmax(0,1fr)]">
          <div />
          <div ref={areaRef} className="relative h-7 cursor-pointer select-none" data-testid="ruler"
            onMouseMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); setHover(((e.clientX - r.left) / r.width) * S.dur) }}
            onMouseLeave={() => setHover(null)} onClick={seekFromEvent}>
            {ticks.map((t) => (
              <div key={t} className="absolute bottom-0" style={{ left: pct(t) }}>
                <div className={cn("w-px", t % 2 === 0 ? "h-2.5 bg-muted-foreground/50" : "h-1.5 bg-border")} />
                {t % 2 === 0 && <span className={cn("absolute bottom-3 font-mono text-[11.5px] text-muted-foreground tabular whitespace-nowrap", t === 0 ? "left-0" : t >= S.dur - 1 ? "right-0" : "-translate-x-1/2")}>{tsec(t)}</span>}
              </div>
            ))}
            {hover !== null && (
              <div className="pointer-events-none absolute top-full z-40 mt-1 -translate-x-1/2" style={{ left: pct(hover) }} data-testid="hover-preview">
                <div className="overflow-hidden rounded-lg border bg-popover shadow-xl">
                  <img src={IMG(nearestFrame(hover))} alt="" className="block h-[132px] w-[72px] object-cover" />
                  <div className="px-1 py-0.5 text-center font-mono text-[10.5px] tabular">{fmt(hover)}</div>
                </div>
              </div>
            )}
          </div>

          <div className="self-center text-[13px] font-semibold">Находки</div>
          <div className="relative cursor-pointer rounded-lg bg-track" style={{ height: laneCount * 32 + 14 }} onClick={seekFromEvent} data-testid="vrow">
            {!items.length && <span className="absolute inset-0 flex items-center justify-center text-[12px] text-muted-foreground" data-testid="vrow-empty">находок нет</span>}
            {items.map((it) => (
              <div key={"iv" + it.id} className="absolute bottom-1 h-1 rounded-full opacity-60" style={{ left: pct(it.iv[0]), width: pct(it.iv[1] - it.iv[0]), background: TONE[tone(it)].color }} />
            ))}
            {placed.map(({ it, lane, flip }) => {
              const tn = tone(it)
              return (
                <HoverCard key={it.id} openDelay={90} closeDelay={60}>
                  <HoverCardTrigger asChild>
                    <button data-testid={"chip-" + it.id} data-tone={tn} onClick={(e) => { e.stopPropagation(); onSelect(it.id) }}
                      className={cn("absolute flex h-[26px] items-center gap-1.5 rounded-lg border bg-card pl-1.5 pr-2.5 text-[12px] shadow-sm transition ease-forte hover:z-20 hover:-translate-y-px hover:shadow-md",
                        flip && "flex-row-reverse pl-2.5 pr-1.5", tn === "rejected" && "opacity-55", sel === it.id ? "z-10 ring-2 ring-sky" : "")}
                      style={{ top: 5 + lane * 32, borderColor: TONE[tn].color, ...(flip ? { right: `calc(100% - ${pct(it.tc)})` } : { left: pct(it.tc) }) }}>
                      <ToneMark it={it} size={16} />
                      <span className={cn("max-w-[150px] truncate font-medium", tn === "rejected" && "line-through")}>{it.short}</span>
                      <span className="font-mono text-[11px] text-muted-foreground tabular">{fmt(it.tc)}</span>
                    </button>
                  </HoverCardTrigger>
                  <HoverCardContent side="top" className="w-auto p-2.5">
                    <div className="flex gap-3">
                      <img src={IMG(it.frames[it.mi ?? 1].t)} alt="" className="h-[148px] w-[81px] rounded-md object-cover" />
                      <div className="w-[200px] text-xs">
                        <div className={cn("text-[10.5px] font-semibold uppercase tracking-[0.1em]", TONE[tn].text)}>{TONE[tn].label}</div>
                        <div className="mt-0.5 text-[13px] font-semibold leading-snug">{typeOf(it.tid).name_ru}</div>
                        <div className="font-mono text-[10.5px] text-muted-foreground">{it.tid}</div>
                        <div className="mt-1.5 font-mono text-muted-foreground">{fmt(it.tc)} · окно {fmt(it.iv[0])}–{fmt(it.iv[1])}</div>
                        <div className="mt-2 text-[11px] text-muted-foreground">нажмите, чтобы открыть карточку</div>
                      </div>
                    </div>
                  </HoverCardContent>
                </HoverCard>
              )
            })}
          </div>

          {all && (
            <>
              <div className="self-center">
                <div className="text-[13px] font-semibold">Эталон</div>
                <div className="text-[10.5px] leading-tight text-muted-foreground">{S.sessions.length ? S.sessions.map((x) => SESSION_BY_KEY[x.type].label).join(" → ") : "тип не определён"}</div>
              </div>
              <PhaseRow S={S} items={items} W={W} onSelect={onSelect} onSeek={onSeek} />
            </>
          )}

          {rows.map((k, i) => {
            const tr = TRACKS.find((x) => x.key === k)!
            return <TrackRow key={k} label={tr.label} code={k} segs={S.tracks[k]} dur={S.dur} W={W} onClick={seekFromEvent} last={i === rows.length - 1}
              empty={k === "cash_location" ? "наличных в кадре нет" : undefined}
              warn={k === "cash_location" && !S.zonesFound.includes("safe") ? `Зона «${ZONE_BY_KEY.safe.label}» не найдена — состояние «в сейфе» не определяется, проверить вручную` : undefined} />
          })}
        </div>

        {all && (
          <div className="mt-3 flex flex-wrap items-center gap-1 text-[12px]" data-testid="phase-chain">
            <span className="mr-1 font-medium text-foreground/80">Ожидалось:</span>
            {S.phases.map((p, i) => { const st = phaseStatus(S, p, items); return (
              <span key={p.n} className="flex items-center gap-1" data-chain={p.n} data-st={st}>
                {i > 0 && <span className="text-muted-foreground">→</span>}
                <span className={cn("rounded-md px-1.5 py-px", PH[st].chain)} title={p.note}>{PH[st].sym} {p.label}</span>
              </span>
            ) })}
          </div>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t pt-3 text-[12px] text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="grid size-4 place-items-center rounded-full bg-destructive text-[9px] font-bold text-white">!</span>нарушение (в вердикте)</span>
          <span className="flex items-center gap-1.5"><span className="grid size-3 rotate-45 place-items-center rounded-[3px] bg-amber" />проверить вручную / вне вердикта</span>
          <span className="flex items-center gap-1.5"><span className="grid size-4 place-items-center rounded-full bg-muted-foreground text-[9px] font-bold text-white">×</span>отклонено</span>
          <span className="flex items-center gap-1.5"><i className="hatch h-3 w-5 rounded-sm" />не проанализировано</span>
          <span className="flex items-center gap-1.5" data-testid="cash-legend"><span className="font-medium text-foreground/80">где деньги:</span>
            {Object.entries(CASH_STATES).map(([k, c]) => <span key={k} className="flex items-center gap-1"><i className="size-2.5 rounded-[3px]" style={{ background: c.color }} />{c.label}</span>)}
          </span>
          <span className="ml-auto flex items-center gap-1"><Eye className="size-3.5" />наведите на шкалу — превью кадра</span>
        </div>
      </div>
      <Overlay S={S} ph={ph} dep={all} />
    </Card>
  )
}

function TrackRow({ label, code, segs, dur, W, onClick, empty, warn, last }: { label: string; code: string; segs: Seg[]; dur: number; W: number; onClick: (e: React.MouseEvent<HTMLElement>) => void; empty?: string; warn?: string; last?: boolean }) {
  return (
    <>
      <div className="truncate self-center text-[13px] text-muted-foreground" title={`${label} (${code})`}>{label}</div>
      <div className="relative h-[22px] cursor-pointer rounded-md bg-track" onClick={onClick} data-track={code} data-last={last || undefined} title={warn}>
        {empty && segs.length === 0 && <span className="absolute inset-y-0 left-2 flex items-center text-[11px] italic text-muted-foreground" data-testid="cash-empty">{empty}</span>}
        {warn && <span className="absolute inset-y-0 right-1.5 flex items-center text-[10.5px] font-medium text-warning" data-testid="cash-warn">⚠ сейф не найден</span>}
        {segs.map((s, i) => {
          const sc = s.state ? CASH_STATES[s.state] : null
          const wpx = ((s.b - s.a) / dur) * W
          return (
            <div key={i}
              className={cn("absolute inset-y-0 flex items-center gap-1.5 overflow-hidden rounded-md px-2 text-[11px] whitespace-nowrap", s.soft ? "border border-dashed border-chip/60 bg-chip/15 text-foreground/80" : "bg-chip text-white", sc && "rounded-none first:rounded-l-md last:rounded-r-md")}
              style={{ left: `${(s.a / dur) * 100}%`, width: `${((s.b - s.a) / dur) * 100}%`, ...(sc ? { background: sc.color } : {}) }}
              data-state={s.state} title={`${fmt(s.a)}–${fmt(s.b)} ${sc ? sc.label : s.label}`}>
              {wpx > 40 && s.label && <span className="truncate">{s.label}</span>}
              {wpx > 40 + s.label.length * 6.5 + 56 && <span className="ml-auto font-mono opacity-75 tabular">{fmt(s.a)}</span>}
            </div>
          )
        })}
      </div>
    </>
  )
}

function Overlay({ S, ph, dep }: { S: Scenario; ph: number; dep: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null)
  useEffect(() => {
    const card = ref.current?.parentElement
    if (!card) return
    const upd = () => {
      const ruler = card.querySelector('[data-testid="ruler"]') as HTMLElement | null
      const last = card.querySelector("[data-last]") as HTMLElement | null
      if (!ruler || !last) return
      const c = card.getBoundingClientRect(), r = ruler.getBoundingClientRect(), l = last.getBoundingClientRect()
      setBox({ left: r.left - c.left, top: r.bottom - c.top - 2, width: r.width, height: l.bottom - r.bottom + 2 })
    }
    upd()
    const ro = new ResizeObserver(upd)
    ro.observe(card)
    return () => ro.disconnect()
  }, [S, dep])
  const pct = (t: number) => `${(Math.min(Math.max(t, 0), S.dur) / S.dur) * 100}%`
  return (
    <div ref={ref} className="pointer-events-none absolute" style={box ? { left: box.left, top: box.top, width: box.width, height: box.height } : { display: "none" }}>
      {S.gaps.map((g, i) => <div key={i} className="hatch absolute inset-y-0 z-[5] rounded-sm" style={{ left: pct(g.a), width: pct(g.b - g.a) }} />)}
      <div className="absolute inset-y-0 z-[6] -ml-px w-0.5 bg-sky" style={{ left: pct(ph) }} data-testid="playhead">
        <div className="absolute -left-[5px] -top-1.5 size-3 rounded-full bg-sky ring-2 ring-card" />
      </div>
    </div>
  )
}

const PH: Record<Phase["st"], { sym: string; dot: string; chain: string }> = {
  ok: { sym: "✓", dot: "bg-success", chain: "bg-success-bg text-success" },
  dev: { sym: "✕", dot: "bg-destructive", chain: "bg-danger-bg font-medium text-destructive" },
  manual: { sym: "?", dot: "bg-amber", chain: "bg-warning-bg font-medium text-warning ring-1 ring-warning-border" },
  na: { sym: "–", dot: "bg-muted-foreground/40", chain: "bg-muted text-muted-foreground" },
  nv: { sym: "◌", dot: "bg-muted-foreground/40", chain: "border border-dashed text-muted-foreground" },
}

function PhaseRow({ S, items, W, onSelect, onSeek }: { S: Scenario; items: Item[]; W: number; onSelect: (id: string) => void; onSeek: (t: number) => void }) {
  const pos = S.phases.filter((p) => p.t !== undefined).map((p) => ({ ...p, st: phaseStatus(S, p, items) }))
  const lanes: number[] = []
  const placed = pos.map((p) => {
    const w = 30 + p.label.length * 6.2, x0 = (p.t! / S.dur) * W, flip = x0 + w > W, left = flip ? x0 - w : x0
    let lane = lanes.findIndex((end) => end + 4 < left)
    if (lane < 0) { lanes.push(0); lane = lanes.length - 1 }
    lanes[lane] = left + w
    return { p, lane, flip }
  })
  const n = Math.max(1, lanes.length)
  const pct = (t: number) => `${(Math.min(Math.max(t, 0), S.dur) / S.dur) * 100}%`
  return (
    <div className="relative rounded-lg bg-track" style={{ height: n * 24 + 12 }} data-testid="phase-row">
      {pos.filter((p) => p.iv).map((p) => (
        <div key={"iv" + p.n} className={cn("absolute bottom-1 h-1.5 rounded-full", p.st === "dev" ? "border border-dashed border-destructive bg-destructive/25" : p.st === "manual" ? "border border-dashed border-amber bg-amber/25" : "bg-success/50")}
          style={{ left: pct(p.iv![0]), width: pct(p.iv![1] - p.iv![0]) }} title={`${p.label}: ${p.note}`} />
      ))}
      {placed.map(({ p, lane, flip }) => (
        <button key={p.n} data-phase={p.n} data-st={p.st} title={`${p.n}. ${p.label} — ${p.note}`}
          onClick={(e) => { e.stopPropagation(); if (p.link) onSelect(p.link); else onSeek(p.t!) }}
          className={cn("absolute flex h-[20px] items-center gap-1 whitespace-nowrap rounded-md px-1.5 text-[11.5px] leading-none transition hover:z-10 hover:shadow",
            flip && "flex-row-reverse",
            p.st === "dev" ? "border border-dashed border-destructive bg-danger-bg font-medium text-destructive" : p.st === "manual" ? "border border-dashed border-warning-border bg-warning-bg font-medium text-warning" : "bg-card text-foreground/80 ring-1 ring-border")}
          style={{ top: 4 + lane * 24, ...(flip ? { right: `calc(100% - ${pct(p.t!)})` } : { left: pct(p.t!) }) }}>
          <span className={cn("grid size-3.5 place-items-center rounded-full text-[8.5px] font-bold text-white", PH[p.st].dot)}>{p.st === "dev" ? "✕" : p.st === "manual" ? "?" : p.n}</span>
          {p.label}
        </button>
      ))}
    </div>
  )
}
