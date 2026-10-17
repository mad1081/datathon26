import { useEffect, useMemo, useRef, useState } from "react"
import { Card, CardAction, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"
import { TRACKS, CASH_STATES, ZONE_BY_KEY, fmt, IMG, nearestFrame, type Item, type Phase, type Scenario, phaseStatus, type Seg } from "@/lib/data"
import { SESSION_BY_KEY } from "@/lib/baseline"

type Props = {
  S: Scenario
  items: Item[]
  sel: string | null
  ph: number
  onSelect: (id: string) => void
  onSeek: (t: number) => void
}

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [w, setW] = useState(600)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w] as const
}

const chipW = (it: Item) => 30 + it.short.length * 6.2 + 46

export function Timeline({ S, items, sel, ph, onSelect, onSeek }: Props) {
  const [areaRef, W] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  const pct = (t: number) => `${(Math.min(Math.max(t, 0), S.dur) / S.dur) * 100}%`

  /* раскладка чипов нарушений по дорожкам, чтобы подписи не налезали */
  const placed = useMemo(() => {
    const lanes: number[] = []
    return [...items].sort((a, b) => a.tc - b.tc).map((it) => {
      const w = chipW(it)
      const x0 = (it.tc / S.dur) * W
      const flip = x0 + w > W
      const left = flip ? x0 - w : x0
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

  return (
    <Card className="relative gap-3">
      <CardHeader>
        <CardTitle className="text-base">Таймлайн</CardTitle>
        <CardAction className="font-mono text-sm text-muted-foreground tabular" data-testid="tltime">{fmt(ph)} / {fmt(S.dur)}</CardAction>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-[150px_minmax(0,1fr)] max-[1360px]:grid-cols-[124px_minmax(0,1fr)] gap-y-1.5">
          {/* линейка с превью кадра при наведении */}
          <div className="text-[11px] text-muted-foreground self-end pb-0.5">сек</div>
          <div
            ref={areaRef}
            className="relative h-6 cursor-pointer select-none"
            data-testid="ruler"
            onMouseMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); setHover(((e.clientX - r.left) / r.width) * S.dur) }}
            onMouseLeave={() => setHover(null)}
            onClick={seekFromEvent}
          >
            {ticks.map((t) => (
              <div key={t} className="absolute bottom-0" style={{ left: pct(t) }}>
                <div className={cn("w-px", t % 2 === 0 ? "h-2 bg-muted-foreground/40" : "h-1.5 bg-border")} />
                {t % 2 === 0 && (
                  <span className={cn("absolute bottom-2.5 font-mono text-[10px] text-muted-foreground tabular whitespace-nowrap",
                    t === 0 ? "left-0" : t >= S.dur - 1 ? "right-0" : "-translate-x-1/2")}>{fmt(t).slice(0, 5)}</span>
                )}
              </div>
            ))}
            {hover !== null && (
              <div className="pointer-events-none absolute top-full mt-1 z-40 -translate-x-1/2" style={{ left: pct(hover) }} data-testid="hover-preview">
                <div className="overflow-hidden rounded-md border bg-popover shadow-lg">
                  <img src={IMG(nearestFrame(hover))} alt="" className="block h-[118px] w-[64px] object-cover" />
                  <div className="px-1 py-0.5 text-center font-mono text-[10px] tabular">{fmt(hover)}</div>
                </div>
              </div>
            )}
          </div>

          {/* эталон: ожидаемая цепочка шагов vs что случилось на видео */}
          <div className="self-center">
            <div className="text-[12.5px] font-semibold">Эталон</div>
            <div className="text-[10px] leading-tight text-muted-foreground">{S.sessions.length ? S.sessions.map((x) => SESSION_BY_KEY[x.type].label).join(" → ") : "тип не определён"}</div>
          </div>
          <PhaseRow S={S} items={items} W={W} onSelect={onSelect} onSeek={onSeek} />

          {/* дорожка нарушений: чипы «тип · таймкод» */}
          <div className="text-[12.5px] font-semibold self-center">Нарушения</div>
          <div className="relative rounded-md bg-track cursor-pointer" style={{ height: laneCount * 26 + 14 }} onClick={seekFromEvent} data-testid="vrow">
            {items.map((it) => (
              <div key={"iv" + it.id} className="absolute bottom-0.5 h-1 rounded-full opacity-50"
                style={{ left: pct(it.iv[0]), width: pct(it.iv[1] - it.iv[0]), background: it.source === "vlm" ? "#8d93a0" : it.color }} />
            ))}
            {placed.map(({ it, lane, flip }) => (
              <HoverCard key={it.id} openDelay={80} closeDelay={60}>
                <HoverCardTrigger asChild>
                  <button
                    data-testid={"chip-" + it.id}
                    onClick={(e) => { e.stopPropagation(); onSelect(it.id) }}
                    className={cn(
                      "absolute flex h-[22px] items-center gap-1.5 rounded-md border bg-card pl-1 pr-2 text-[11px] shadow-sm transition hover:z-20 hover:shadow-md",
                      flip && "flex-row-reverse pl-2 pr-1",
                      it.status === "rejected" && "opacity-50",
                      sel === it.id ? "z-10 ring-2 ring-primary" : "",
                    )}
                    style={{ top: 4 + lane * 26, ...(flip ? { right: `calc(100% - ${pct(it.tc)})` } : { left: pct(it.tc) }) }}
                  >
                    <span className={cn("grid size-4 shrink-0 place-items-center text-[10px] font-bold text-white", it.omission ? "rounded-[4px]" : "rounded-full")}
                      style={{ background: it.source === "vlm" ? "#8d93a0" : it.color }}>{it.source === "vlm" ? "?" : "!"}</span>
                    <span className={cn("max-w-[140px] truncate font-medium", it.status === "rejected" && "line-through")}>{it.short}</span>
                    <span className="font-mono text-muted-foreground tabular">{fmt(it.tc)}</span>
                  </button>
                </HoverCardTrigger>
                <HoverCardContent side="top" className="w-auto p-2">
                  <div className="flex gap-2.5">
                    <img src={IMG(it.frames[it.mi ?? 1].t)} alt="" className="h-[148px] w-[81px] rounded object-cover" />
                    <div className="w-[170px] text-xs">
                      <div className="font-semibold leading-snug">{it.title}</div>
                      <div className="mt-1 font-mono text-muted-foreground">{fmt(it.tc)} · окно {fmt(it.iv[0])}–{fmt(it.iv[1])}</div>
                      <div className="mt-1 text-muted-foreground">{it.zoneMissing ? "зона не найдена" : `${Math.round(it.conf * 100)}%${it.demoConf ? " (демо)" : ""}`} · {it.source === "vlm" ? "VLM" : "правило"}</div>
                      <div className="mt-2 text-[11px] text-muted-foreground">кадр «момент» · нажмите, чтобы открыть</div>
                    </div>
                  </div>
                </HoverCardContent>
              </HoverCard>
            ))}
          </div>

          {/* дорожки событий */}
          {TRACKS.map((tr) => (
            <TrackRow key={tr.key} label={tr.label} code={tr.key} segs={S.tracks[tr.key]} dur={S.dur} W={W} onClick={seekFromEvent}
              empty={tr.key === "cash_location" ? "наличных в кадре нет" : undefined}
              warn={tr.key === "cash_location" && !S.zonesFound.includes("safe") ? `Зона «${ZONE_BY_KEY.safe.label}» не найдена — состояние «в сейфе» не определяется, проверить вручную` : undefined} />
          ))}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1 text-[11.5px]" data-testid="phase-chain">
          <span className="mr-1 font-medium text-foreground/80">Ожидалось:</span>
          {S.phases.map((p, i) => { const st = phaseStatus(S, p, items); return (
            <span key={p.n} className="flex items-center gap-1" data-chain={p.n} data-st={st}>
              {i > 0 && <span className="text-muted-foreground">→</span>}
              <span className={cn("rounded px-1.5 py-px", PH[st].chain)} title={p.note}>{PH[st].sym} {p.label}</span>
            </span>
          ) })}
        </div>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-muted-foreground">
          <span className="flex items-center gap-1.5"><i className="grid size-3.5 place-items-center rounded-full bg-primary text-[9px] not-italic font-bold text-white">!</i>правило из базы</span>
          <span className="flex items-center gap-1.5"><i className="grid size-3.5 place-items-center rounded-full bg-[#8d93a0] text-[9px] not-italic font-bold text-white">?</i>второй судья (VLM)</span>
          <span className="flex items-center gap-1.5"><i className="size-3.5 rounded-[4px] bg-primary" />по бездействию</span>
          <span className="flex items-center gap-1.5"><i className="hatch h-3 w-5 rounded-sm" />не проанализировано</span>
          <span className="flex items-center gap-1.5" data-testid="cash-legend"><span className="font-medium text-foreground/80">где деньги:</span>
            {Object.entries(CASH_STATES).map(([k, c]) => (
              <span key={k} className="flex items-center gap-1"><i className="size-2.5 rounded-[3px]" style={{ background: c.color }} />{c.label}</span>
            ))}
          </span>
          <span className="ml-auto">наведите на линейку — превью кадра</span>
        </div>
      </CardContent>
      <Overlay S={S} ph={ph} />
    </Card>
  )
}

function TrackRow({ label, code, segs, dur, W, onClick, empty, warn }: { label: string; code: string; segs: Seg[]; dur: number; W: number; onClick: (e: React.MouseEvent<HTMLElement>) => void; empty?: string; warn?: string }) {
  return (
    <>
      <div className="truncate text-[12.5px] text-muted-foreground self-center" title={`${label} (${code})`}>{label}</div>
      <div className="relative h-[18px] rounded-md bg-track cursor-pointer" onClick={onClick} data-track={code} title={warn}>
        {empty && segs.length === 0 && <span className="absolute inset-y-0 left-2 flex items-center text-[10.5px] italic text-muted-foreground" data-testid="cash-empty">{empty}</span>}
        {warn && <span className="absolute inset-y-0 right-1.5 flex items-center text-[10px] text-warning" data-testid="cash-warn">⚠ сейф не найден</span>}
        {segs.map((s, i) => {
          const sc = s.state ? CASH_STATES[s.state] : null
          const wpx = ((s.b - s.a) / dur) * W
          return (
            <div key={i}
              className={cn("absolute inset-y-0 flex items-center gap-1.5 overflow-hidden rounded-md px-1.5 text-[10.5px] whitespace-nowrap", s.soft ? "border border-dashed border-chip/60 bg-chip/25 text-foreground/80" : "bg-chip text-white", sc && "rounded-none first:rounded-l-md last:rounded-r-md")}
              style={{ left: `${(s.a / dur) * 100}%`, width: `${((s.b - s.a) / dur) * 100}%`, ...(sc ? { background: sc.color } : {}) }}
              data-state={s.state}
              title={`${fmt(s.a)}–${fmt(s.b)} ${sc ? sc.label : s.label}`}>
              {wpx > 40 && s.label && <span className="truncate">{s.label}</span>}
              {wpx > 40 + s.label.length * 6 + 50 && <span className="ml-auto font-mono opacity-70 tabular">{fmt(s.a)}</span>}
            </div>
          )
        })}
      </div>
    </>
  )
}

/* оверлей поверх сетки: непроанализированные отрезки + плейхед; координаты берутся из DOM */
function Overlay({ S, ph }: { S: Scenario; ph: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null)
  useEffect(() => {
    const card = ref.current?.parentElement
    if (!card) return
    const upd = () => {
      const ruler = card.querySelector('[data-testid="ruler"]') as HTMLElement | null
      const last = card.querySelector('[data-track="document_card"]') as HTMLElement | null
      if (!ruler || !last) return
      const c = card.getBoundingClientRect(), r = ruler.getBoundingClientRect(), l = last.getBoundingClientRect()
      setBox({ left: r.left - c.left, top: r.bottom - c.top - 2, width: r.width, height: l.bottom - r.bottom + 2 })
    }
    upd()
    const ro = new ResizeObserver(upd)
    ro.observe(card)
    return () => ro.disconnect()
  }, [S])
  const pct = (t: number) => `${(Math.min(Math.max(t, 0), S.dur) / S.dur) * 100}%`
  return (
    <div ref={ref} className="pointer-events-none absolute" style={box ? { left: box.left, top: box.top, width: box.width, height: box.height } : { display: "none" }}>
      {S.gaps.map((g, i) => (
        <div key={i} className="hatch absolute inset-y-0 z-[5] rounded-sm" style={{ left: pct(g.a), width: pct(g.b - g.a) }} />
      ))}
      <div className="absolute inset-y-0 z-[6] -ml-px w-0.5 bg-primary" style={{ left: pct(ph) }} data-testid="playhead">
        <div className="absolute -left-[4px] -top-1.5 size-2.5 rounded-full bg-primary ring-2 ring-card" />
      </div>
    </div>
  )
}

const PH: Record<Phase["st"], { sym: string; dot: string; chain: string }> = {
  ok: { sym: "✓", dot: "bg-success", chain: "bg-success-bg text-success" },
  dev: { sym: "✕", dot: "bg-destructive", chain: "bg-danger-bg font-medium text-destructive" },
  manual: { sym: "!", dot: "bg-warning", chain: "bg-warning-bg font-medium text-warning ring-1 ring-warning-border" },
  na: { sym: "–", dot: "bg-muted-foreground/40", chain: "bg-muted text-muted-foreground" },
  nv: { sym: "◌", dot: "bg-muted-foreground/40", chain: "border border-dashed text-muted-foreground" },
}

/* дорожка «Эталон»: шаги на своих местах во времени; отклонения — красным, пропущенный шаг — пунктиром там, где ожидался */
function PhaseRow({ S, items, W, onSelect, onSeek }: { S: Scenario; items: Item[]; W: number; onSelect: (id: string) => void; onSeek: (t: number) => void }) {
  const pos = S.phases.filter((p) => p.t !== undefined).map((p) => ({ ...p, st: phaseStatus(S, p, items) }))
  const lanes: number[] = []
  const placed = pos.map((p) => {
    const w = 26 + p.label.length * 5.6
    const x0 = (p.t! / S.dur) * W
    const flip = x0 + w > W
    const left = flip ? x0 - w : x0
    let lane = lanes.findIndex((end) => end + 4 < left)
    if (lane < 0) { lanes.push(0); lane = lanes.length - 1 }
    lanes[lane] = left + w
    return { p, lane, flip }
  })
  const n = Math.max(1, lanes.length)
  const pct = (t: number) => `${(Math.min(Math.max(t, 0), S.dur) / S.dur) * 100}%`
  return (
    <div className="relative rounded-md bg-track" style={{ height: n * 20 + 12 }} data-testid="phase-row">
      {pos.filter((p) => p.iv).map((p) => (
        <div key={"iv" + p.n} className={cn("absolute bottom-0.5 h-1.5 rounded-full", p.st === "dev" ? "border border-dashed border-destructive bg-destructive/25" : p.st === "manual" ? "border border-dashed border-warning bg-warning/25" : "bg-success/50")}
          style={{ left: pct(p.iv![0]), width: pct(p.iv![1] - p.iv![0]) }} title={`${p.label}: ${p.note}`} />
      ))}
      {placed.map(({ p, lane, flip }) => (
        <button key={p.n} data-phase={p.n} data-st={p.st} title={`${p.n}. ${p.label} — ${p.note}`}
          onClick={(e) => { e.stopPropagation(); if (p.link) onSelect(p.link); else onSeek(p.t!) }}
          className={cn("absolute flex h-[17px] items-center gap-1 whitespace-nowrap rounded px-1 text-[10.5px] leading-none transition hover:z-10 hover:shadow",
            flip && "flex-row-reverse",
            p.st === "dev" ? "border border-dashed border-destructive bg-danger-bg font-medium text-destructive" : p.st === "manual" ? "border border-dashed border-warning-border bg-warning-bg font-medium text-warning" : "bg-card text-foreground/80 ring-1 ring-border")}
          style={{ top: 3 + lane * 20, ...(flip ? { right: `calc(100% - ${pct(p.t!)})` } : { left: pct(p.t!) }) }}>
          <span className={cn("grid size-3 place-items-center rounded-full text-[8px] font-bold text-white", PH[p.st].dot)}>{p.st === "dev" ? "✕" : p.st === "manual" ? "!" : p.n}</span>
          {p.label}
        </button>
      ))}
    </div>
  )
}
