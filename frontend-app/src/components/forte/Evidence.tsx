import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, Maximize2 } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { IMG, REGIONS, VH, VW, fmt, type Region, type ZoneKey } from "@/lib/data"
import { ZoneOverlay } from "./Zones"

export type Shot = { t: number; region: Region | null; cap: string; moment: boolean; gap?: string }

function FrameImg({ s, ill, big, zones }: { s: Shot; ill: boolean; big?: boolean; zones: ZoneKey[] | null }) {
  const m = s.region ? REGIONS[s.region] : null
  return (
    <div className={cn("relative overflow-hidden bg-black", big ? "h-[74vh] rounded-xl" : "rounded-lg")} style={{ aspectRatio: `${VW} / ${VH}` }}>
      <img src={IMG(s.t)} alt={`кадр ${fmt(s.t)}`} className="block size-full object-cover" />
      {zones && !s.gap && <ZoneOverlay found={zones} light={!big} />}
      {m && (
        <div className="absolute rounded-[5px] border-[2.5px] border-coral shadow-[0_0_0_1px_rgba(0,0,0,.35)]"
          style={{ left: `${(m[0] / VW) * 100}%`, top: `${(m[1] / VH) * 100}%`, width: `${(m[2] / VW) * 100}%`, height: `${(m[3] / VH) * 100}%` }} />
      )}
      {s.gap && <div className="hatch absolute inset-0 grid place-items-center bg-muted/80 p-3 text-center text-xs text-foreground">{s.gap}</div>}
      {ill && <Badge className="absolute bottom-1.5 left-1.5 bg-black/70 text-[10px] text-white">иллюстрация</Badge>}
    </div>
  )
}

/* 1–3 кадра (до / момент / после) с таймкодами; клик — лайтбокс с листанием (← →) */
export function FrameStrip({ shots, ill, zones, onSeek, accent = "var(--primary)" }: { shots: Shot[]; ill: boolean; zones: ZoneKey[] | null; onSeek: (t: number) => void; accent?: string }) {
  const [zi, setZi] = useState<number | null>(null)
  const zoomable = shots.map((s, i) => (s.gap ? -1 : i)).filter((i) => i >= 0)
  const step = (d: number) => setZi((cur) => { if (cur === null) return cur; const k = zoomable.indexOf(cur); return zoomable[(k + d + zoomable.length) % zoomable.length] })
  useEffect(() => {
    if (zi === null) return
    const h = (e: KeyboardEvent) => { if (e.key === "ArrowRight") step(1); if (e.key === "ArrowLeft") step(-1) }
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h)
  })
  const z = zi !== null ? shots[zi] : null
  return (
    <>
      <div className={cn("grid gap-2.5", shots.length === 1 ? "grid-cols-[minmax(0,140px)]" : shots.length === 2 ? "grid-cols-2" : "grid-cols-3")} data-testid="frames">
        {shots.map((s, i) => (
          <div key={i}>
            <button className="group relative block w-full rounded-lg text-left transition ease-forte" data-testid={"frame-" + i}
              style={s.moment ? { boxShadow: `0 0 0 2px var(--card), 0 0 0 4px ${accent}` } : undefined}
              onClick={() => { onSeek(s.t); if (!s.gap) setZi(i) }}>
              <FrameImg s={s} ill={ill} zones={zones} />
              {!s.gap && <span className="absolute right-1.5 top-1.5 grid size-7 place-items-center rounded-full bg-white/90 text-primary opacity-0 shadow transition group-hover:opacity-100"><Maximize2 className="size-3.5" /></span>}
            </button>
            <div className="mt-1.5 flex items-center justify-between text-[12px]">
              <span className={cn(s.moment ? "font-semibold" : "text-muted-foreground")} style={s.moment ? { color: accent } : undefined}>{s.cap}</span>
              <span className="font-mono text-muted-foreground tabular">{s.gap ? "—" : fmt(s.t)}</span>
            </div>
          </div>
        ))}
      </div>
      <Dialog open={z !== null} onOpenChange={(o) => !o && setZi(null)}>
        <DialogContent className="w-auto max-w-none rounded-2xl sm:max-w-none" data-testid="lightbox">
          <DialogHeader>
            <DialogTitle>Кадр {z && fmt(z.t)} · {z?.cap}</DialogTitle>
            <DialogDescription>Исходный кадр из видео, без распознавания лиц. Коралловая рамка — область находки; контуры — зоны.</DialogDescription>
          </DialogHeader>
          {z && (
            <div className="flex items-center gap-3">
              <button onClick={() => step(-1)} aria-label="Предыдущий кадр" className="grid size-10 place-items-center rounded-full border bg-card text-muted-foreground hover:text-foreground disabled:opacity-30" disabled={zoomable.length < 2}><ChevronLeft className="size-5" /></button>
              <FrameImg s={z} ill={ill} big zones={zones} />
              <button onClick={() => step(1)} aria-label="Следующий кадр" className="grid size-10 place-items-center rounded-full border bg-card text-muted-foreground hover:text-foreground disabled:opacity-30" disabled={zoomable.length < 2}><ChevronRight className="size-5" /></button>
            </div>
          )}
          <div className="flex justify-center gap-1.5">
            {zoomable.map((i) => <button key={i} onClick={() => setZi(i)} className={cn("h-1.5 rounded-full transition-all", i === zi ? "w-6 bg-sky" : "w-1.5 bg-border")} aria-label={"кадр " + (i + 1)} />)}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
