/* Клиент заданий анализа. Контракт жюри: POST /api/v1/analyze (multipart file, X-API-Key) → { job_id, status };
   GET /api/v1/jobs/{job_id} → { job_id, status: queued|processing|done|failed, progress?, stage?, ...result }.
   В макете используется SimulatedJobClient; HttpJobClient готов к подключению реального сервиса. */
export type JobStatus = "queued" | "processing" | "done" | "failed"
export type StageKey = "upload" | "frames" | "zones" | "steps" | "rules"
export const STAGES: { key: StageKey; title: string; sub: string; weight: number }[] = [
  { key: "upload", title: "Загрузка файла", sub: "POST /api/v1/analyze", weight: 1 },
  { key: "frames", title: "Извлечение кадров", sub: "2 кадра/с, до 640 px по длинной стороне", weight: 1.2 },
  { key: "zones", title: "Детекция зон", sub: "стол, сейф, счётная машинка, сторона клиента", weight: 1 },
  { key: "steps", title: "Анализ шагов процедуры", sub: "сессии (приём / выдача / без клиента), эталон Правил № 231", weight: 1.6 },
  { key: "rules", title: "Проверка правил", sub: "rules.json v0.4 · пороги · count_in_verdict", weight: 1.2 },
]
export type JobSnapshot = { job_id: string; status: JobStatus; stage: StageKey | null; progress: number; error?: string }

export interface JobClient {
  submit(file: File | null, name: string): Promise<{ job_id: string; status: JobStatus }>
  poll(job_id: string): Promise<JobSnapshot>
}

export class HttpJobClient implements JobClient {
  private base: string
  private apiKey: string
  constructor(base: string, apiKey: string) { this.base = base; this.apiKey = apiKey }
  async submit(file: File | null) {
    if (!file) throw new Error("нет файла")
    const fd = new FormData(); fd.append("file", file)
    const r = await fetch(`${this.base}/api/v1/analyze`, { method: "POST", headers: { "X-API-Key": this.apiKey }, body: fd })
    if (!r.ok) throw new Error(`analyze: HTTP ${r.status}`)
    return r.json()
  }
  async poll(job_id: string): Promise<JobSnapshot> {
    const r = await fetch(`${this.base}/api/v1/jobs/${job_id}`, { headers: { "X-API-Key": this.apiKey } })
    if (!r.ok) return { job_id, status: "failed", stage: null, progress: 0, error: `HTTP ${r.status}` } /* не показывать зелёный вердикт при ошибке */
    const j = await r.json()
    return { job_id, status: j.status, stage: j.stage ?? null, progress: j.progress ?? (j.status === "done" ? 1 : 0), error: j.error }
  }
}

/* имитация: queued ~0.8 c, затем этапы по весам; fail=true — ошибка на этапе «Проверка правил» */
export class SimulatedJobClient implements JobClient {
  private t0 = new Map<string, number>()
  private totalMs: number
  private fail: boolean
  constructor(totalMs = 7000, fail = false) { this.totalMs = totalMs; this.fail = fail }
  async submit() {
    const h = Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("")
    const id = `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
    this.t0.set(id, performance.now())
    return { job_id: id, status: "queued" as const }
  }
  async poll(job_id: string): Promise<JobSnapshot> {
    const el = performance.now() - (this.t0.get(job_id) ?? performance.now())
    const q = 800
    if (el < q) return { job_id, status: "queued", stage: null, progress: 0 }
    const W = STAGES.reduce((a, s) => a + s.weight, 0)
    const k = Math.min(1, (el - q) / this.totalMs)
    let acc = 0
    for (const s of STAGES) {
      const a = acc / W, b = (acc + s.weight) / W
      if (k < b) {
        if (this.fail && s.key === "rules" && (k - a) / (b - a) > 0.4) return { job_id, status: "failed", stage: s.key, progress: k, error: "Видео повреждено после 00:12 — кадры не декодируются (демо ошибки)" }
        return { job_id, status: "processing", stage: s.key, progress: k }
      }
      acc += s.weight
    }
    return { job_id, status: "done", stage: null, progress: 1 }
  }
}
