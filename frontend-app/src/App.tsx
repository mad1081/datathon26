import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"
import { Header } from "@/components/forte/Header"
import { VideoPlayer } from "@/components/forte/VideoPlayer"
import { Timeline } from "@/components/forte/Timeline"
import { type Shot } from "@/components/forte/Evidence"
import { VerdictBanner } from "@/components/forte/VerdictBanner"
import { MoreDetails } from "@/components/forte/MoreDetails"
import { Findings } from "@/components/forte/Findings"
import { Detail } from "@/components/forte/Detail"
import { Actions } from "@/components/forte/Actions"
import { Taxonomy } from "@/components/forte/Taxonomy"
import { typeOf, SESSION_BY_KEY } from "@/lib/baseline"
import { JsonPanel } from "@/components/forte/JsonPanel"
import { UploadScreen } from "@/components/forte/Upload"
import { ServerResult } from "@/components/forte/ServerResult"
import type { ApiResult } from "@/lib/api"
import { SCENARIOS, OPS, buildResult, compliance, isViolation, needsReview, type Item, type ScenarioKey } from "@/lib/data"

const parseHash = () => {
  const h = location.hash.slice(1).split("&")
  return {
    screen: h.includes("upload") ? ("upload" as const) : ("result" as const),
    sc: (h.find((x) => x in SCENARIOS) as ScenarioKey) || "real",
    dark: h.includes("dark"),
  }
}

export default function App() {
  const init = parseHash()
  const [screen, setScreen] = useState<"result" | "upload">(init.screen)
  const [scKey, setScKey] = useState<ScenarioKey>(init.sc)
  const [dark, setDark] = useState(init.dark)
  const S = SCENARIOS[scKey]
  const [items, setItems] = useState<Item[]>(() => structuredClone(SCENARIOS[init.sc].items))
  const [sel, setSel] = useState<string | null>(SCENARIOS[init.sc].sel)
  const [ph, setPh] = useState(SCENARIOS[init.sc].start)
  const [playing, setPlaying] = useState(false)
  const [zones, setZones] = useState(true)
  const [taxOpen, setTaxOpen] = useState(location.hash.includes("taxonomy"))
  const [custom, setCustom] = useState<{ name: string; size: number; url: string } | null>(null)
  const [apiResult, setApiResult] = useState<ApiResult | null>(null) // ответ сервиса после загрузки в режиме «Сервер»
  const vref = useRef<HTMLVideoElement>(null)
  const pending = useRef<number | null>(SCENARIOS[init.sc].start)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => { document.documentElement.classList.toggle("dark", dark) }, [dark])

  const seek = useCallback((t: number) => {
    const v = vref.current
    const tt = Math.max(0, Math.min(S.dur, t))
    setPh(tt)
    if (v && v.readyState >= 1) v.currentTime = tt
    else pending.current = tt
  }, [S.dur])

  const loadScenario = useCallback((k: ScenarioKey) => {
    const s = SCENARIOS[k]
    setScKey(k); setItems(structuredClone(s.items)); setSel(s.sel); setPh(s.start)
    const v = vref.current
    if (v && v.readyState >= 1) v.currentTime = s.start
    else pending.current = s.start
  }, [])

  // плавный плейхед во время воспроизведения
  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => { if (vref.current) setPh(vref.current.currentTime); raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  const select = useCallback((id: string) => {
    setSel(id)
    if (id.startsWith("gap")) seek(S.gaps[+id.slice(3)].a)
    else { const it = items.find((x) => x.id === id); if (it) seek(it.tc) }
  }, [S, items, seek])

  const setStatus = (id: string, s: "confirmed" | "rejected") => {
    const it = items.find((x) => x.id === id)
    if (!it) return
    const next = it.status === s ? "pending" : s
    setItems((cur) => cur.map((x) => (x.id === id ? { ...x, status: next } : x)))
    if (next === "pending") toast("Возвращено на проверку", { description: it.title })
    else if (next === "confirmed") toast.success("Подтверждено — JSON обновлён", { description: it.title })
    else toast("Отклонено — осталось в JSON с rejected_by_operator", { description: it.title })
  }

  const v = items.filter(isViolation).length
  const r = items.filter(needsReview).length
  const g = S.gaps.length
  const result = useMemo(() => buildResult(S, items), [S, items])
  const labels = useMemo(() => items.filter((x) => x.status !== "pending").map((x) => ({
    video: S.file, type: typeOf(x.tid).name_ru, type_id: x.tid, title: x.title, baseline_step: x.step, rule_id: x.rule, source: x.source, timecode_sec: x.tc, window_sec: x.iv, confidence: x.conf, operator_status: OPS[x.status],
  })), [items, S.file])

  const selItem = sel && !sel.startsWith("gap") ? items.find((x) => x.id === sel) ?? null : null
  const selGap = sel && sel.startsWith("gap") ? S.gaps[+sel.slice(3)] : null
  const ill = S.src !== "real"
  const shots: Shot[] = selItem
    ? selItem.frames.map((f, i) => ({ t: f.t, region: f.region, cap: (selItem.flab ?? ["до", "момент", "после"])[i], moment: i === (selItem.mi ?? 1) }))
    : selGap
      ? [{ t: 4.0, region: null, cap: "до", moment: false }, { t: 5.0, region: null, cap: "пропуск", moment: true, gap: "Кадры не проанализированы" }, { t: 7.5, region: null, cap: "после", moment: false }]
      : (S.sample ?? []).map((t) => ({ t, region: null, cap: "выборка", moment: false }))

  const [more, setMore] = useState<"baseline" | "json">(location.hash.includes("json") ? "json" : "baseline")
  // «к шагу процедуры» из карточки → панель «Действия кассира»
  const gotoStep = () => {
    setMore("baseline")
    requestAnimationFrame(() => document.querySelector("[data-testid=actions]")?.scrollIntoView({ behavior: "smooth", block: "start" }))
  }


  const comp = useMemo(() => {
    if (!S.sessions.length) return null
    let ok = 0, total = 0
    for (const ss of S.sessions) { const c = compliance(S, ss.type, items); ok += c.ok; total += c.total }
    return { ok, total }
  }, [S, items])
  const firstViolation = () => {
    const t = items.filter(isViolation).sort((a, b) => a.tc - b.tc)[0]?.id
    if (!t) return
    select(t)
    requestAnimationFrame(() => document.querySelector('[data-testid="detail"]')?.scrollIntoView({ behavior: "smooth", block: "nearest" }))
  }
  const reviewFirst = () => {
    const t = items.find(needsReview)?.id ?? (S.gaps.length ? "gap0" : null)
    if (!t) return
    select(t)
    requestAnimationFrame(() => document.querySelector(`[data-id="${t}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest" }))
  }

  const openFile = (f: File) => {
    setCustom({ name: f.name, size: f.size, url: URL.createObjectURL(f) })
    toast("Видео открыто в плеере", { description: "Таймлайн и находки — по-прежнему демо-данные." })
  }

  return (
    <div className="min-h-screen">
      <Header screen={screen} onScreen={setScreen} scenario={scKey} onScenario={(k) => { loadScenario(k); setApiResult(null); setScreen("result") }}
        dark={dark} onDark={setDark} fileName={custom?.name ?? S.file} />

      {screen === "upload" ? (
        <UploadScreen onDone={(f, res) => {
          setApiResult(res ?? null)
          if (f?.url) setCustom({ name: f.name, size: f.size, url: f.url })
          loadScenario("real"); setScreen("result")
          toast.success("Обработка завершена", { description: res ? `Ответ сервиса: ${res.verdict === "violation" ? "есть признаки нарушений" : "нарушений не найдено"} — см. «Действия кассира» и «Ответ API (JSON)»` : "Демо-данные реального сценария" })
        }} />
      ) : apiResult ? (
        <main className="mx-auto flex max-w-[1100px] flex-col gap-5 px-6 py-5">
          <ServerResult result={apiResult} file={custom?.name ?? "видео"} />
          <MoreDetails tab={more} onTab={setMore} json={
            <JsonPanel result={apiResult} labels={labels} file={custom?.name ?? S.file} />
          } baseline={
            <Actions result={apiResult} ph={ph} onSeek={seek} />
          } onTaxonomy={() => setTaxOpen(true)} />
        </main>
      ) : (
        <main className="mx-auto flex max-w-[1440px] flex-col gap-5 px-6 py-5 max-[1360px]:gap-4 max-[1360px]:px-4 max-[1360px]:py-4" key={scKey}>
          <VerdictBanner v={v} r={r} g={g} dur={S.dur} src={S.src} file={custom?.name ?? S.file}
            session={S.sessions.length ? S.sessions.map((x) => SESSION_BY_KEY[x.type].label).join(" → ") : "не определена"}
            comp={comp} onFirstViolation={firstViolation} onReview={reviewFirst} />
          <div className="grid grid-cols-[260px_minmax(0,1fr)_440px] items-start gap-5 max-[1360px]:grid-cols-[236px_minmax(0,1fr)_408px] max-[1360px]:gap-4">
            <div className="sticky top-20 flex min-w-0 flex-col gap-4">
              <VideoPlayer ref={vref} ph={ph} playing={playing} customSrc={custom?.url ?? null}
                fileInfo={custom ? { name: custom.name, line: `${(custom.size / 1048576).toFixed(1)} МБ · открыт локально` } : { name: "sample.mov", line: "H.264 · 464×848 (портрет) · 30 к/с · 17,07 с" }}
                onToggle={() => { const el = vref.current; if (el) { if (el.paused) void el.play(); else el.pause() } }}
                onPick={() => fileInput.current?.click()}
                zones={zones} onZones={setZones} zonesFound={S.zonesFound}
                onTime={(t) => { if (!playing) setPh(t) }} onPlaying={setPlaying}
                onMeta={() => { const el = vref.current; if (el && pending.current != null) { el.currentTime = pending.current; pending.current = null } }} />
              <input ref={fileInput} type="file" accept=".mp4,.mov,video/*" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) openFile(f); e.target.value = "" }} />
            </div>
            <div className="flex min-w-0 flex-col gap-5 max-[1360px]:gap-4">
              <Timeline S={S} items={items} sel={sel} ph={ph} onSelect={select} onSeek={seek} />
              <Findings items={items} gaps={S.gaps} sel={sel} onSelect={select} />
            </div>
            <div className="min-w-0">
              <Detail S={S} item={selItem} gap={selGap} onGoto={seek} onStatus={setStatus} onStep={gotoStep} shots={shots} ill={ill} zones={zones && !custom ? S.zonesFound : null} />
            </div>
          </div>
          <MoreDetails tab={more} onTab={setMore} json={
            <JsonPanel result={apiResult ?? result} labels={labels} file={custom?.name ?? S.file} />
          } baseline={
            <Actions result={apiResult} ph={ph} onSeek={seek} />
          } onTaxonomy={() => setTaxOpen(true)} />
        </main>
      )}
      <Taxonomy open={taxOpen} onOpen={setTaxOpen} items={items} />
      <Toaster position="bottom-center" theme={dark ? "dark" : "light"} />
    </div>
  )
}
