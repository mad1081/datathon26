/* Экран загрузки. Дропзона и вертикальный степпер адаптированы по мотивам 21st.dev:
   «Upload Dropzone Empty State» (arihantcodes, id 29988: счётчик dragenter/leave, строка файла с прогрессом)
   и «Vertical Titled Stepper» (sean0205, id 29815: нумерованные шаги, соединительная линия, check/loader).
   Установка из реестра 21st требует API-ключ, поэтому собрано на примитивах shadcn. */
import { useEffect, useRef, useState } from "react"
import { CheckIcon, LoaderCircleIcon, UploadCloud, FileVideo, PlayCircle } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const STEPS = [
  { title: "Загрузка", sub: "файл → сервис, POST /api/v1/analyze", dur: 1400 },
  { title: "Раскадровка", sub: "2 кадра/с, кадры до 640 px", dur: 1600 },
  { title: "Анализ", sub: "окна 4 с, шаг 2 с → VLM + правила → нормы", dur: 3400 },
  { title: "Готово", sub: "вердикт, нарушения, кадры, JSON", dur: 0 },
]

type F = { name: string; size: number; url: string | null }

export function UploadScreen({ onDone }: { onDone: (f: F | null) => void }) {
  const [over, setOver] = useState(false)
  const [file, setFile] = useState<F | null>(null)
  const [step, setStep] = useState(-1)
  const [p, setP] = useState(0)
  const depth = useRef(0)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (step < 0 || step >= 3) return
    const t0 = performance.now(), d = STEPS[step].dur
    const id = setInterval(() => {
      const k = Math.min(1, (performance.now() - t0) / d)
      setP(k)
      if (k >= 1) { clearInterval(id); setStep((s) => s + 1); setP(0) }
    }, 60)
    return () => clearInterval(id)
  }, [step])

  const start = (f: F) => { setFile(f); setStep(0); setP(0) }
  const pick = (fl: FileList | null) => { const x = fl?.[0]; if (x) start({ name: x.name, size: x.size, url: URL.createObjectURL(x) }) }
  const total = step < 0 ? 0 : step >= 3 ? 100 : Math.round(((step + p) / 3) * 100)

  return (
    <div className="mx-auto grid max-w-[1100px] grid-cols-[minmax(0,1fr)_340px] gap-4 p-6" data-testid="upload-screen">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Новая проверка видео</CardTitle>
          <CardDescription>MP4 / MOV с камеры кассы. Обработка до 5 минут; лица не распознаются, звук не анализируется.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            onDragEnter={(e) => { e.preventDefault(); depth.current++; setOver(true) }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={(e) => { e.preventDefault(); depth.current = Math.max(0, depth.current - 1); if (!depth.current) setOver(false) }}
            onDrop={(e) => { e.preventDefault(); depth.current = 0; setOver(false); pick(e.dataTransfer.files) }}
            className={cn("relative grid place-items-center rounded-xl border-2 border-dashed px-6 py-14 text-center transition",
              over ? "border-primary bg-accent" : "border-border bg-muted/40")}
            data-testid="dropzone"
          >
            <div className="relative mb-4 grid size-16 place-items-center rounded-2xl bg-card shadow-sm ring-1 ring-border">
              <UploadCloud className="size-7 text-primary" />
            </div>
            <div className="text-[15px] font-semibold">{over ? "Отпустите файл" : "Перетащите видео с кассы"}</div>
            <div className="mt-1 text-[13px] text-muted-foreground">или выберите на компьютере</div>
            <div className="mt-4 flex gap-2">
              <Button onClick={() => input.current?.click()}><FileVideo />Выбрать файл</Button>
              <Button variant="outline" onClick={() => start({ name: "sample.mov", size: 3476145, url: null })} data-testid="demo-run"><PlayCircle />Демо-прогон на sample.mov</Button>
            </div>
            <div className="mt-3 text-[11.5px] text-muted-foreground">MP4, MOV · до 5 мин · портрет и альбом</div>
            <input ref={input} type="file" accept=".mp4,.mov,video/*" className="sr-only" onChange={(e) => { pick(e.target.files); e.target.value = "" }} />
          </div>

          {file && (
            <div className="flex items-center gap-3 rounded-xl border bg-card px-3 py-2.5" data-testid="file-row">
              <FileVideo className={cn("size-5 shrink-0", step >= 3 ? "text-success" : "text-muted-foreground")} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="truncate text-[13.5px] font-medium">{file.name}</span>
                  <span className="shrink-0 font-mono text-[12px] text-muted-foreground tabular">{(file.size / 1048576).toFixed(1)} МБ · {total}%</span>
                </div>
                <Progress value={total} className="mt-1.5 h-1.5" />
              </div>
            </div>
          )}
          <p className="text-[11.5px] text-muted-foreground">Имитация: в макете анализ не запускается, после «Готово» открывается результат с демо-данными (для sample.mov — реальный сценарий).</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Статус обработки</CardTitle>
          <CardDescription>{step < 0 ? "Ожидает файл" : step >= 3 ? "Готово" : `Шаг ${step + 1} из 4`}</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="relative" data-testid="stepper">
            {STEPS.map((s, i) => {
              const state = step > i || (i === 3 && step >= 3) ? "completed" : step === i ? "active" : "inactive"
              return (
                <li key={s.title} className="relative flex gap-3 pb-7 last:pb-0" data-state={state}>
                  {i < STEPS.length - 1 && (
                    <span className={cn("absolute left-3 top-7 h-[calc(100%-2rem)] w-0.5 -translate-x-1/2 rounded-full", step > i ? "bg-success" : "bg-border")} />
                  )}
                  <span className={cn("relative z-10 grid size-6 shrink-0 place-items-center rounded-full text-[11px] font-semibold ring-1",
                    state === "completed" && "bg-success text-white ring-success",
                    state === "active" && "bg-primary text-primary-foreground ring-primary",
                    state === "inactive" && "bg-muted text-muted-foreground ring-border")}>
                    {state === "completed" ? <CheckIcon className="size-3.5" /> : state === "active" ? <LoaderCircleIcon className="size-3.5 animate-spin" /> : i + 1}
                  </span>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="flex items-center gap-2">
                      <span className={cn("text-[13.5px] font-semibold", state === "inactive" && "text-muted-foreground")}>{s.title}</span>
                      {state === "active" && <Badge variant="outline" className="font-mono text-[10px] tabular">{Math.round(p * 100)}%</Badge>}
                    </div>
                    <div className="text-[12px] text-muted-foreground">{s.sub}</div>
                    {state === "active" && <Progress value={p * 100} className="mt-2 h-1" />}
                  </div>
                </li>
              )
            })}
          </ol>
          <Button className="mt-6 w-full" disabled={step < 3} onClick={() => onDone(file)} data-testid="open-result">Открыть результат</Button>
        </CardContent>
      </Card>
    </div>
  )
}
