import { forwardRef } from "react"
import { Pause, Play, FolderOpen, Shapes, ChevronRight } from "lucide-react"
import { Toggle } from "@/components/ui/toggle"
import { ZoneOverlay } from "./Zones"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { fmt, ZONES, type ZoneKey } from "@/lib/data"
import { cn } from "@/lib/utils"

type Props = {
  ph: number
  playing: boolean
  customSrc: string | null
  fileInfo: { name: string; line: string }
  onToggle: () => void
  onPick: () => void
  onTime: (t: number) => void
  onPlaying: (p: boolean) => void
  onMeta: () => void
  zones: boolean
  onZones: (v: boolean) => void
  zonesFound: ZoneKey[]
}

export const VideoPlayer = forwardRef<HTMLVideoElement, Props>(function VideoPlayer(
  { ph, playing, customSrc, fileInfo, onToggle, onPick, onTime, onPlaying, onMeta, zones, onZones, zonesFound }, ref) {
  return (
    <Card className="gap-0 p-3 bg-plum text-white ring-0 dark:bg-card dark:ring-1" data-testid="player">
      <div className="relative overflow-hidden rounded-xl bg-black" style={{ aspectRatio: "464 / 848" }}>
        <video
          ref={ref}
          data-testid="video"
          className="block size-full object-contain"
          controls muted playsInline preload="auto" poster="./video/poster.jpg"
          onTimeUpdate={(e) => onTime(e.currentTarget.currentTime)}
          onSeeked={(e) => onTime(e.currentTarget.currentTime)}
          onPlay={() => onPlaying(true)} onPause={() => onPlaying(false)}
          onLoadedMetadata={onMeta}
          {...(customSrc ? { src: customSrc } : {})}
        >
          {!customSrc && <source src="./video/sample.mov" type="video/mp4" />}
          {!customSrc && <source src="./video/sample.webm" type="video/webm" />}
        </video>
        {zones && !customSrc && <ZoneOverlay found={zonesFound} />}
        <Toggle size="sm" pressed={zones} onPressedChange={onZones} disabled={!!customSrc} data-testid="zones-toggle"
          className="absolute left-2 top-9 h-6 min-w-0 gap-1 rounded-md bg-black/55 px-1.5 text-[11px] text-white backdrop-blur hover:bg-black/70 hover:text-white data-[state=on]:bg-white data-[state=on]:text-plum">
          <Shapes className="size-3" />Зоны
        </Toggle>
        <Badge className="pointer-events-none absolute left-2 top-2 bg-black/55 text-white backdrop-blur">CAM-01 · касса</Badge>
        <Badge className="pointer-events-none absolute right-2 top-2 bg-black/55 font-mono text-white tabular backdrop-blur" data-testid="vtime">{fmt(ph)}</Badge>
      </div>
      <div className="mt-3 px-0.5 text-[12px] leading-relaxed text-white/70">
        <div className="font-semibold text-white">{fileInfo.name}</div>
        <div>{fileInfo.line}</div>
      </div>
      {zones && !customSrc && (
        <details className="group mt-2 text-[11px] text-white/75" data-testid="zone-details">
          <summary className="flex cursor-pointer list-none items-center gap-1 font-medium text-white/85 marker:hidden">
            <ChevronRight className="size-3.5 transition-transform group-open:rotate-90" />Легенда зон · найдено {zonesFound.length}/{ZONES.length}
          </summary>
          <div className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1" data-testid="zone-legend">
            {ZONES.map((z) => {
              const ok = zonesFound.includes(z.key)
              return (
                <span key={z.key} className={cn("flex items-center gap-1", !ok && "text-white/45")}>
                  <i className="size-2.5 rounded-[3px]" style={ok ? { background: z.color } : { border: `1px dashed ${z.color}` }} />
                  {z.label}{!ok && " — не найдена"}
                </span>
              )
            })}
          </div>
        </details>
      )}
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="inverse" onClick={onPick} className="flex-1 dark:bg-secondary dark:text-foreground"><FolderOpen />Открыть файл</Button>
        <Button size="sm" variant="inverse" onClick={onToggle} className="dark:bg-secondary dark:text-foreground" data-testid="play">
          {playing ? <Pause /> : <Play />}{playing ? "Пауза" : "Играть"}
        </Button>
      </div>
      <p className="mt-2 text-[11px] leading-snug text-white/45">Файл открывается локально в плеере; анализ в макете не запускается.</p>
    </Card>
  )
})
