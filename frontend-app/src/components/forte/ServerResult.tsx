import type { ApiResult } from "@/lib/api"

/* Результат реального сервиса: вердикт, нарушения, кадры-доказательства и норма из ответа API. */
type Frame = { timestamp_sec?: number; image_base64?: string; role?: string }
type RuleRef = { doc?: string; clause?: string; quote?: string; url?: string } | null
type Viol = { type?: string; type_id?: string; timecode?: string; timecode_sec?: number; description?: string; observed?: string;
  evidence_frames?: Frame[]; rule_ref?: RuleRef }

export function ServerResult({ result, file }: { result: ApiResult; file: string }) {
  const bad = result.verdict === "violation"
  const viols = (result.violations ?? []) as unknown as Viol[]
  const timeline = (result.timeline ?? []) as { t: number; event: string }[]
  return (
    <div className="flex flex-col gap-5">
      <div className={`rounded-lg px-5 py-4 text-xl font-bold ${bad ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300" : "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"}`}>
        {bad ? "Обнаружены признаки возможных нарушений" : "Нарушение не обнаружено"}
        <div className="mt-1 text-sm font-normal text-muted-foreground">Файл: {file}{result.scenario ? ` · Сценарий: ${result.scenario}` : ""}</div>
      </div>
      {viols.map((v, i) => (
        <div key={i} className="rounded-lg border bg-card p-4">
          <div className="text-lg font-semibold">{v.type ?? v.type_id}</div>
          <div className="mt-1 text-sm text-muted-foreground">Таймкод: {v.timecode ?? ""} ({Math.round(v.timecode_sec ?? 0)} с)</div>
          {v.observed ? <div className="mt-2 text-sm">Что видно: {v.observed}</div> : null}
          <div className="mt-3 flex flex-wrap gap-3">
            {(v.evidence_frames ?? []).map((f, j) => (
              <figure key={j} className="w-40">
                <img className="w-40 rounded border" src={`data:image/jpeg;base64,${f.image_base64 ?? ""}`} alt="кадр" />
                <figcaption className="mt-1 text-xs text-muted-foreground">{f.timestamp_sec?.toFixed(1)} с</figcaption>
              </figure>
            ))}
          </div>
          {v.rule_ref ? (
            <div className="mt-3 text-sm">
              <b>{v.rule_ref.doc}</b>, {v.rule_ref.clause}: «{v.rule_ref.quote}»{" "}
              {v.rule_ref.url ? <a className="text-primary underline" href={v.rule_ref.url} target="_blank" rel="noreferrer">adilet.zan.kz</a> : null}
            </div>
          ) : null}
          {v.description ? <details className="mt-2 text-sm text-muted-foreground"><summary>Полное описание</summary>{v.description}</details> : null}
        </div>
      ))}
      {timeline.length ? (
        <div className="rounded-lg border bg-card p-4 text-sm">
          <div className="mb-2 font-semibold">Хронология</div>
          {timeline.map((e, i) => <div key={i}><b>{Math.round(e.t)} с</b> — {e.event}</div>)}
        </div>
      ) : null}
    </div>
  )
}
