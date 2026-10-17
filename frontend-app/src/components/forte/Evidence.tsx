import { useState } from "react"
import { Maximize2 } from "lucide-react"
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { IMG, REGIONS, VH, VW, fmt, type Region, type ZoneKey } from "@/lib/data"
import { ZoneOverlay } from "./Zones"

export type Shot = { t: number; region: Region | null; cap: string; moment: boolean; gap?: string }

function FrameImg({ s, ill, big, zones }: { s: Shot; ill: boolean; big?: boolean; zones: ZoneKey[] | null }) {
  const m = s.region ? REGIONS[s.region] : null
  return (
    <div className={cn("relative overflow-hidden rounded-lg bg-black", big ? "h-[78vh]" : "")} style={{ aspectRatio: `${VW} / ${VH}` }}>
      <img src={IMG(s.t)} alt={`кадр ${fmt(s.t)}`} className="block size-full object-cover" />
      {zones && !s.gap && <ZoneOverlay found={zones} light={!big} />}
      {m && (
        <div className="absolute rounded-[5px] border-[2.5px] border-[#F27A5E] shadow-[0_0_0_1px_rgba(0,0,0,.3)]"
          style={{ left: `${(m[0] / VW) * 100}%`, top: `${(m[1] / VH) * 100}%`, width: `${(m[2] / VW) * 100}%`, height: `${(m[3] / VH) * 100}%` }} />
      )}
      {s.gap && <div className="hatch absolute inset-0 grid place-items-center bg-muted/80 p-3 text-center text-xs text-foreground">{s.gap}</div>}
      {ill && <Badge className="absolute bottom-1.5 left-1.5 bg-black/70 text-[10px] text-white">иллюстрация</Badge>}
    </div>
  )
}

export function Evidence({ shots, ill, onSeek, zones }: { shots: Shot[]; ill: boolean; onSeek: (t: number) => void; zones: ZoneKey[] | null }) {
  const [zoom, setZoom] = useState<Shot | null>(null)
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="text-base">Кадры-доказательства</CardTitle>
        <CardAction className="font-mono text-xs text-muted-foreground">timecode_sec = кадр «момент»</CardAction>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3" data-testid="frames">
          {shots.map((s, i) => (
            <div key={i}>
              <button
                className={cn("group relative block w-full rounded-lg text-left transition", s.moment && "ring-2 ring-primary ring-offset-2 ring-offset-card")}
                onClick={() => { onSeek(s.t); if (!s.gap) setZoom(s) }}
                data-testid={"frame-" + i}
              >
                <FrameImg s={s} ill={ill} zones={zones} />
                {!s.gap && <span className="absolute right-1.5 top-1.5 grid size-6 place-items-center rounded-md bg-black/55 text-white opacity-0 transition group-hover:opacity-100"><Maximize2 className="size-3.5" /></span>}
              </button>
              <div className="mt-2 flex items-center justify-between text-[12.5px]">
                <span className={cn(s.moment ? "font-semibold text-primary" : "text-muted-foreground")}>{s.cap}</span>
                <span className="font-mono text-muted-foreground tabular">{s.gap ? "—" : fmt(s.t)}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
      <Dialog open={!!zoom} onOpenChange={(o) => !o && setZoom(null)}>
        <DialogContent className="w-auto max-w-none sm:max-w-none">
          <DialogHeader>
            <DialogTitle>Кадр {zoom && fmt(zoom.t)} · {zoom?.cap}</DialogTitle>
            <DialogDescription>Исходный кадр из видео, без распознавания лиц. Рамка — область, к которой относится находка; цветные контуры — зоны (сейф, стол, машинка, сторона клиента).</DialogDescription>
          </DialogHeader>
          {zoom && <div className="flex justify-center"><FrameImg s={zoom} ill={ill} big zones={zones} /></div>}
        </DialogContent>
      </Dialog>
    </Card>
  )
}
