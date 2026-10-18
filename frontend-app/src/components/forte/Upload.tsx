/* Экран загрузки + прогресс задания. Структура под реальный API: JobClient (lib/api.ts) — submit → poll раз в 500 мс.
   В макете SimulatedJobClient; для боевого режима подставить new HttpJobClient(base, apiKey). Дропзона/степпер — по мотивам
   21st.dev «Upload Dropzone Empty State» и «Vertical Titled Stepper», собрано на примитивах shadcn в стиле Forte. */
import { useEffect, useMemo, useRef, useState } from "react"
import { Check, LoaderCircle, UploadCloud, FileVideo, PlayCircle, OctagonAlert, RotateCcw, ShieldCheck, EyeOff, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { HttpJobClient, STAGES, SimulatedJobClient, type ApiResult, type JobClient, type JobSnapshot } from "@/lib/api"

type F = { name: string; size: number; url: string | null }
const ACCEPT = /\.(mov|mp4)$/i
// UI, раздаваемый самим сервисом, ходит в API того же адреса
const DEFAULT_BASE = location.protocol.startsWith("http") ? location.origin : ""

export function UploadScreen({ onDone }: { onDone: (f: F | null, result?: ApiResult) => void }) {
  const [over, setOver] = useState(false)
  const [file, setFile] = useState<F | null>(null)
  const [snap, setSnap] = useState<JobSnapshot | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [failDemo, setFailDemo] = useState(location.hash.includes("fail"))
  const depth = useRef(0)
  const input = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<"demo" | "server">("server")
  const [base, setBase] = useState(DEFAULT_BASE)
  const [apiKey, setApiKey] = useState("") // только в памяти страницы, не сохраняется
  const server = mode === "server"
  const client = useMemo<JobClient>(() => server ? new HttpJobClient(base, apiKey) : new SimulatedJobClient(7000, failDemo), [server, base, apiKey, failDemo])

  useEffect(() => {
    if (!snap || snap.status === "done" || snap.status === "failed") return
    const id = setTimeout(async () => {
      try { setSnap(await client.poll(snap.job_id)) }
      catch (e) { setSnap({ ...snap, status: "failed", error: `нет связи с сервисом: ${(e as Error).message}` }) }
    }, server ? 1500 : 250)
    return () => clearTimeout(id)
  }, [snap, client, server])
  useEffect(() => {
    if (snap?.status !== "done") return
    const id = setTimeout(() => onDone(file, snap.result), 1100)
    return () => clearTimeout(id)
  }, [snap?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  const start = async (f: F, raw: File | null) => {
    setErr(null)
    if (server && (!base || !apiKey)) { setErr("Укажите адрес сервиса и API-ключ"); return }
    setFile(f)
    try {
      const r = await client.submit(raw, f.name)
      setSnap({ job_id: r.job_id, status: r.status, stage: null, progress: 0 })
    } catch (e) {
      setFile(null); setErr(`Не удалось отправить видео: ${(e as Error).message}`)
    }
  }
  const pick = (fl: FileList | null) => {
    const x = fl?.[0]; if (!x) return
    if (!ACCEPT.test(x.name)) { setErr(`«${x.name}» — нужен .mov или .mp4`); return }
    void start({ name: x.name, size: x.size, url: URL.createObjectURL(x) }, x)
  }
  const reset = () => { setSnap(null); setFile(null); setErr(null) }
  const busy = !!snap && snap.status !== "failed"
  const stIdx = snap?.stage ? STAGES.findIndex((s) => s.key === snap.stage) : snap?.status === "done" ? STAGES.length : -1
  const pct = Math.round((snap?.progress ?? 0) * 100)

  return (
    <div className="mx-auto max-w-[1180px] px-6 py-8" data-testid="upload-screen">
      <div className="mb-6">
        <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-slate">Новая проверка</div>
        <h1 className="mt-1 text-[32px] font-bold leading-tight tracking-[-0.01em]">Загрузите видео с камеры кассы</h1>
        <p className="mt-1 max-w-[640px] text-[15px] text-muted-foreground">Сервис найдёт признаки нарушений кассовой дисциплины и покажет кадры-доказательства со ссылками на нормы НБ РК.</p>
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_400px] gap-5">
        <section className="rounded-2xl border bg-card p-6">
          {!snap ? (
            <>
              <div className="mb-4 flex flex-wrap items-end gap-3" data-testid="server-settings">
                <div className="flex rounded-lg border border-hairline p-0.5 text-[13px] font-medium">
                  {(["server", "demo"] as const).map((m) => (
                    <button key={m} onClick={() => setMode(m)} data-testid={"mode-" + m}
                      className={cn("rounded-md px-3 py-1.5 transition-colors", mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
                      {m === "server" ? "Сервер" : "Демо"}
                    </button>
                  ))}
                </div>
                {server && (
                  <>
                    <label className="flex min-w-[260px] flex-1 flex-col gap-1 text-[12px] text-muted-foreground">Адрес сервиса
                      <input value={base} onChange={(e) => setBase(e.target.value.trim())} placeholder="https://…" data-testid="api-base"
                        className="h-9 rounded-md border border-hairline bg-background px-3 font-mono text-[13px] text-foreground" />
                    </label>
                    <label className="flex w-[260px] flex-col gap-1 text-[12px] text-muted-foreground">API-ключ (X-API-Key)
                      <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value.trim())} autoComplete="off" data-testid="api-key"
                        className="h-9 rounded-md border border-hairline bg-background px-3 font-mono text-[13px] text-foreground" />
                    </label>
                  </>
                )}
              </div>
              <div
                onDragEnter={(e) => { e.preventDefault(); depth.current++; setOver(true) }}
                onDragOver={(e) => e.preventDefault()}
                onDragLeave={(e) => { e.preventDefault(); depth.current = Math.max(0, depth.current - 1); if (!depth.current) setOver(false) }}
                onDrop={(e) => { e.preventDefault(); depth.current = 0; setOver(false); pick(e.dataTransfer.files) }}
                className={cn("relative grid min-h-[340px] place-items-center overflow-hidden rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors ease-forte",
                  over ? "border-brand bg-accent" : "border-hairline bg-background")}
                data-testid="dropzone">
                <div className="pointer-events-none absolute inset-x-0 top-0 h-1.5" style={{ background: "var(--grad-secondary)" }} />
                <div>
                  <div className={cn("mx-auto grid size-[72px] place-items-center rounded-full text-white shadow-lg transition-transform", over && "scale-110")} style={{ background: "var(--grad-hero)" }}>
                    <UploadCloud className="size-8" />
                  </div>
                  <div className="mt-5 text-[20px] font-semibold">{over ? "Отпустите, чтобы загрузить" : "Перетащите видео сюда"}</div>
                  <div className="mt-1 text-[14px] text-muted-foreground">или выберите файл на компьютере</div>
                  <div className="mt-6 flex justify-center gap-3">
                    <Button size="lg" onClick={() => input.current?.click()} data-testid="pick"><FileVideo />Выбрать файл</Button>
                    {!server && <Button size="lg" variant="outline" className="border-primary text-primary hover:text-primary dark:border-white/30 dark:text-foreground" onClick={() => void start({ name: "sample.mov", size: 9_400_000, url: null }, null)} data-testid="demo-run"><PlayCircle />Демо: sample.mov</Button>}
                  </div>
                  <div className="mt-4 flex justify-center gap-2 text-[12.5px] text-muted-foreground">
                    {[".mov", ".mp4", "до 5 мин", "портрет и альбом"].map((t) => <span key={t} className="rounded-full border border-hairline bg-card px-2.5 py-0.5">{t}</span>)}
                  </div>
                  {err && <div className="mt-4 text-[13px] font-medium text-destructive" data-testid="upload-err">{err}</div>}
                </div>
                <input ref={input} type="file" accept=".mov,.mp4,video/mp4,video/quicktime" className="sr-only" onChange={(e) => { pick(e.target.files); e.target.value = "" }} />
              </div>
              {!server && <label className="mt-4 flex w-fit cursor-pointer items-center gap-2 text-[12.5px] text-muted-foreground">
                <input type="checkbox" checked={failDemo} onChange={(e) => setFailDemo(e.target.checked)} className="accent-[var(--primary)]" data-testid="fail-demo" />имитировать ошибку обработки (failed)
              </label>}
            </>
          ) : (
            <div className="fade-in" data-testid="job">
              <div className="flex items-center gap-3 rounded-xl bg-muted p-3">
                <div className="grid size-11 place-items-center rounded-lg bg-card text-brand"><FileVideo className="size-5" /></div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[15px] font-semibold">{file?.name}</div>
                  <div className="text-[12.5px] text-muted-foreground">{file ? (file.size / 1048576).toFixed(1) + " МБ" : ""}</div>
                </div>
                <StatusPill s={snap.status} />
              </div>
              <div className="mt-5 flex items-end justify-between">
                <div>
                  <div className="text-[12px] font-semibold uppercase tracking-[0.14em] text-slate">job_id</div>
                  <code className="font-mono text-[13px]" data-testid="job-id">{snap.job_id}</code>
                </div>
                <div className="text-right text-[32px] font-bold leading-none tabular text-primary dark:text-foreground" data-testid="job-pct">{pct}%</div>
              </div>
              <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-surface-gray">
                <div className={cn("relative h-full rounded-full transition-[width] duration-300 ease-forte", snap.status === "failed" ? "bg-destructive" : "bg-sky")} style={{ width: `${Math.max(pct, snap.status === "queued" ? 3 : 0)}%` }}>
                  {busy && snap.status !== "done" && <div className="shimmer absolute inset-0" />}
                </div>
              </div>
              <div className="mt-2 text-[13px] text-muted-foreground" data-testid="job-stage">
                {snap.status === "queued" ? "В очереди — ожидаем свободный обработчик" : snap.status === "processing" ? (stIdx >= 0 ? STAGES[stIdx].title + " — " + STAGES[stIdx].sub : "Обработка…") : snap.status === "done" ? "Готово — открываем результат…" : "Обработка прервана"}
              </div>
              {snap.status === "failed" && (
                <div className="mt-5 flex gap-3 rounded-xl border border-destructive/30 bg-danger-bg p-4" data-testid="job-failed">
                  <OctagonAlert className="mt-0.5 size-5 shrink-0 text-destructive" />
                  <div className="flex-1">
                    <div className="text-[15px] font-semibold text-destructive">status: failed</div>
                    <p className="mt-0.5 text-[13.5px]">{snap.error}</p>
                    <p className="mt-1 text-[12.5px] text-muted-foreground">Вердикт не выносится — зелёный результат при ошибке не показывается.</p>
                    <div className="mt-3 flex gap-2">
                      <Button onClick={reset} data-testid="retry"><RotateCcw />Загрузить заново</Button>
                    </div>
                  </div>
                </div>
              )}
              {snap.status === "done" && <div className="mt-5"><Button size="lg" onClick={() => onDone(file, snap.result)} data-testid="open-result">Открыть результат</Button></div>}
            </div>
          )}
        </section>

        <aside className="rounded-2xl border bg-card p-6" data-testid="stepper">
          <h2 className="text-[20px] font-semibold">Этапы обработки</h2>
          <div className="mt-0.5 text-[13px] text-muted-foreground">POST /api/v1/analyze → GET /api/v1/jobs/{"{job_id}"}</div>
          <ol className="mt-5">
            <Step i={0} title="В очереди" sub="status: queued" state={!snap ? "todo" : snap.status === "queued" ? "active" : "done"} last={false} />
            {STAGES.map((s, i) => {
              const st = !snap || snap.status === "queued" ? "todo" : snap.status === "done" || i < stIdx ? "done" : i === stIdx ? (snap.status === "failed" ? "fail" : "active") : "todo"
              return <Step key={s.key} i={i + 1} title={s.title} sub={s.sub} state={st} last={i === STAGES.length - 1} />
            })}
          </ol>
          <div className="mt-5 grid gap-2 border-t pt-4 text-[12.5px] text-muted-foreground">
            <div className="flex items-center gap-2"><EyeOff className="size-4 text-brand" />Лица не распознаются, звук не анализируется</div>
            <div className="flex items-center gap-2"><ShieldCheck className="size-4 text-brand" />Обработка локально, видео не уходит наружу</div>
            <div className="flex items-center gap-2"><Clock className="size-4 text-brand" />{server ? "Реальный сервис: до 5 минут на видео" : "Имитация: ~8 с"}</div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function StatusPill({ s }: { s: JobSnapshot["status"] }) {
  const M = {
    queued: ["queued", "bg-muted text-muted-foreground ring-1 ring-border"],
    processing: ["processing", "bg-[color-mix(in_oklab,var(--sky)_18%,transparent)] text-[#0B6E99] dark:text-sky"],
    done: ["done", "bg-success-bg text-success"],
    failed: ["failed", "bg-danger-bg text-destructive"],
  }[s]
  return <span className={cn("rounded-full px-2.5 py-1 font-mono text-[12px] font-semibold", M[1])} data-testid="job-status">{M[0]}</span>
}

function Step({ i, title, sub, state, last }: { i: number; title: string; sub: string; state: "todo" | "active" | "done" | "fail"; last: boolean }) {
  return (
    <li className="relative flex gap-3 pb-5 last:pb-0" data-state={state}>
      {!last && <span className={cn("absolute left-4 top-9 h-[calc(100%-36px)] w-0.5 -translate-x-1/2 rounded-full", state === "done" ? "bg-primary dark:bg-brand" : "bg-surface-gray")} />}
      <span className={cn("relative z-10 grid size-8 shrink-0 place-items-center rounded-full text-[13px] font-semibold transition-colors",
        state === "done" ? "bg-primary text-white dark:bg-brand" : state === "active" ? "bg-card text-primary ring-2 ring-sky dark:text-foreground" : state === "fail" ? "bg-destructive text-white" : "bg-muted text-muted-foreground")}>
        {state === "done" ? <Check className="size-4" /> : state === "active" ? <LoaderCircle className="size-4 animate-spin" /> : state === "fail" ? "!" : i}
      </span>
      <span className="pt-1">
        <span className={cn("block text-[14.5px] font-semibold leading-tight", state === "todo" && "text-muted-foreground")}>{title}</span>
        <span className="mt-0.5 block text-[12.5px] text-muted-foreground">{sub}</span>
      </span>
    </li>
  )
}
