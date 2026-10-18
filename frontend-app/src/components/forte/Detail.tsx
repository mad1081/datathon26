import { Check, X, ExternalLink, Eye, EyeOff, ShieldCheck, ShieldQuestion, Quote, Play, ArrowRight, Images, CircleCheck } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { cn } from "@/lib/utils"
import { ZONE_BY_KEY, TONE, fmt, tone, type Gap, type Item, type Scenario, type ZoneKey } from "@/lib/data"
import { BASELINE, CATEGORIES, SESSIONS, STEPS, STRENGTH, OUTSIDE_VERDICT, typeOf, type SessionKey } from "@/lib/baseline"
import { RULE_ACTS, isCiteVerified, type RuleCite } from "@/lib/rules"
import { FrameStrip, type Shot } from "./Evidence"
import { ToneMark } from "./Timeline"

/* источник нормы: ссылка на adilet.zan.kz с якорем + бейдж «сверено» (якорь и цитата найдены в локальной копии) / «не сверено» */
function RuleCiteBlock({ c }: { c: RuleCite }) {
  const a = RULE_ACTS[c.act]
  const ok = isCiteVerified(c.url)
  const anchor = c.url.split("#")[1]
  return (
    <div className="rounded-xl border bg-card p-3.5" data-testid="cite" data-verified={ok}>
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-semibold leading-snug">{a?.short ?? c.act}, {c.clause}</div>
          <div className="text-[11.5px] text-muted-foreground">{a?.number}</div>
        </div>
        {ok ? (
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-success-bg px-2 py-0.5 text-[11px] font-medium text-success" data-testid="cite-verified"><ShieldCheck className="size-3.5" />сверено</span>
        ) : (
          <span className="flex shrink-0 items-center gap-1 rounded-full border border-dashed border-warning-border bg-warning-bg px-2 py-0.5 text-[11px] font-medium text-warning" data-testid="unverified"><ShieldQuestion className="size-3.5" />не сверено</span>
        )}
      </div>
      <div className="mt-2 flex gap-2 border-l-2 border-brand/40 pl-2.5 text-[13px] italic leading-relaxed">
        <Quote className="mt-0.5 size-3.5 shrink-0 text-brand" /><span>{c.quote}</span>
      </div>
      <a href={c.url} target="_blank" rel="noopener" className="mt-2.5 inline-flex items-center gap-1 text-[12.5px] font-medium text-[#185AC5] hover:underline dark:text-sky" data-testid="adilet-link">
        adilet.zan.kz{anchor ? <code className="font-mono text-[11.5px]">#{anchor}</code> : " (без якоря)"}<ExternalLink className="size-3" />
      </a>
    </div>
  )
}

type Props = {
  S: Scenario
  item: Item | null
  gap: Gap | null
  onGoto: (t: number) => void
  onStatus: (id: string, s: "confirmed" | "rejected") => void
  onStep: (sk: SessionKey, step: string) => void
  shots: Shot[]
  ill: boolean
  zones: ZoneKey[] | null
}

export function Detail({ S, item, gap, onGoto, onStatus, onStep, shots, ill, zones }: Props) {
  if (gap) return (
    <Card data-testid="detail"><CardContent className="space-y-3">
      <div className={cn("text-[12px] font-semibold uppercase tracking-[0.12em]", TONE.manual.text)}>не проанализировано · проверить вручную</div>
      <h2 className="text-[22px] font-bold leading-tight">Отрезок {fmt(gap.a)}–{fmt(gap.b)}</h2>
      <FrameStrip shots={shots} ill={ill} zones={null} onSeek={onGoto} accent="var(--amber)" />
      <p className="text-[13.5px] leading-relaxed">Модель не смотрела этот кусок: {gap.why}. Нарушение внутри него не исключено — просмотрите видео вручную. В ответе API отрезок лежит в <code className="font-mono text-xs">unanalyzed_ranges</code>.</p>
      <Badge variant="outline" className="rounded-full border-warning-border bg-warning-bg text-warning">Вердикт по этому отрезку не выносится</Badge>
    </CardContent></Card>
  )
  if (!item) return (
    <Card data-testid="detail"><CardContent className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="grid size-11 place-items-center rounded-full bg-success-bg text-success"><CircleCheck className="size-6" /></div>
        <div><div className="text-[12px] font-semibold uppercase tracking-[0.12em] text-slate">итог</div><h2 className="text-[20px] font-bold">Нарушений не обнаружено</h2></div>
      </div>
      <ul className="divide-y rounded-xl bg-muted px-3 text-[13px]">
        {[`Проанализировано 100% видео (${fmt(S.dur)})`, "Нарушений выше порога правил: 0", "Моментов для ручной проверки: 0", "Непроанализированных отрезков: 0"].map((t) => (
          <li key={t} className="flex items-center gap-2 py-2"><Check className="size-4 text-success" />{t}</li>
        ))}
      </ul>
      {shots.length > 0 && <>
        <div className="flex items-center gap-1.5 text-[12.5px] font-medium text-muted-foreground"><Images className="size-4" />Кадры-выборка из видео</div>
        <FrameStrip shots={shots} ill={ill} zones={zones} onSeek={onGoto} accent="var(--success)" />
      </>}
      <p className="text-[12px] text-muted-foreground">Пороги правил — из rules.json (0,60–0,85).</p>
    </CardContent></Card>
  )
  const it = item
  const T = typeOf(it.tid), cat = CATEGORIES[T.cat]
  const kick = it.kind === "violation" ? "нарушение · " + (it.omission ? "по бездействию" : "по действию") : "проверить вручную · " + (it.source === "vlm" ? "второй судья (VLM)" : it.zoneMissing ? "зона не найдена" : !T.count_in_verdict ? "вне вердикта (rules.json)" : it.thr !== null && it.conf < it.thr ? "ниже порога" : "нужен контекст")
  const step = it.step
  const sk = step ? ((S.sessions.map((x) => x.type).find((k) => BASELINE[k].includes(step)) ?? SESSIONS.find((x) => BASELINE[x.key].includes(step))!.key) as SessionKey) : null
  const stepN = sk && step ? BASELINE[sk].indexOf(step) + 1 : 0
  const cOn = it.status === "confirmed", rOn = it.status === "rejected"
  const win = it.iv[0] !== it.tc || it.iv[1] !== it.tc ? ` (окно ${fmt(it.iv[0])}–${fmt(it.iv[1])})` : ""
  const tn = tone(it), TN = TONE[tn]
  return (
    <Card data-testid="detail" className="gap-0 py-0"><div className="h-1.5" style={{ background: TN.color }} />
    <CardContent className="space-y-3.5 py-5">
      <div>
        <div className="flex items-center gap-2">
          <ToneMark it={it} size={18} />
          <span className={cn("text-[12px] font-semibold uppercase tracking-[0.12em]", TN.text)} data-testid="detail-tone">{TN.label}</span>
          <button onClick={() => onGoto(it.tc)} data-testid="detail-tc"
            className="ml-auto flex h-8 items-center gap-1.5 rounded-full border px-3 font-mono text-[12.5px] font-medium tabular text-primary transition hover:bg-accent dark:text-foreground">
            <Play className="size-3.5 fill-current" />{fmt(it.tc)}
          </button>
        </div>
        <h2 className="mt-2 text-[22px] font-bold leading-[1.2] tracking-[-0.01em]" data-testid="detail-type">{T.name_ru}</h2>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11.5px]" data-testid="type-row">
          <code className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11.5px]" data-type-id={it.tid}>type_id: {it.tid}</code>
          <span className="flex items-center gap-1 rounded-full border px-2 py-0.5" style={{ borderColor: cat.color + "66", color: cat.color }}><i className="size-1.5 rounded-full" style={{ background: cat.color }} />{cat.label}</span>
          <span className={cn("rounded-full px-2 py-0.5", STRENGTH[T.strength].cls)}>{STRENGTH[T.strength].label}</span>
          <span className="font-mono text-muted-foreground">порог {T.threshold} · {it.zoneMissing ? "зона не найдена" : Math.round(it.conf * 100) + "%" + (it.demoConf ? " демо" : "")}</span>
        </div>
        <div className="mt-1 text-[12.5px] text-muted-foreground">{kick} · {it.title}{win}</div>
        {!T.count_in_verdict && <div className="mt-2 rounded-lg bg-warning-bg px-3 py-2 text-[12.5px] font-medium text-warning ring-1 ring-warning-border" data-testid="outside-verdict">{OUTSIDE_VERDICT} — по rules.json (count_in_verdict: false)</div>}
      </div>

      <FrameStrip shots={shots} ill={ill} zones={zones} onSeek={onGoto} accent={TN.color} />

      <p className="text-[13.5px] leading-relaxed">{it.desc}{it.demoConf && <span className="text-muted-foreground"> Уверенность {Math.round(it.conf * 100)}% — демо-значение.</span>}</p>
      {sk && step ? (
        <button onClick={() => onStep(sk, step)} data-testid="goto-step"
          className="flex w-full items-center gap-2 rounded-xl border px-3 py-2 text-left text-[12.5px] transition hover:border-primary/50 hover:bg-accent">
          <span className="min-w-0 flex-1"><span className="block text-[11px] uppercase tracking-[0.08em] text-muted-foreground">отклонение от эталона</span><b>{SESSIONS.find((x) => x.key === sk)!.label}</b> · шаг {stepN} «{STEPS[step].title}»</span>
          <ArrowRight className="size-4 shrink-0 text-primary dark:text-foreground" />
        </button>
      ) : (
        <div className="rounded-xl border border-dashed px-3 py-2 text-[12.5px] text-muted-foreground" data-testid="goto-step">вне эталона — тип не привязан к шагу процедуры</div>
      )}
      {it.zoneMissing && (
        <Alert className="border-warning-border bg-warning-bg text-warning" data-testid="zone-missing">
          <ShieldQuestion />
          <AlertDescription className="text-[12px] text-warning">Зона «{ZONE_BY_KEY[it.zoneMissing].label}» не найдена детектором — зависимая проверка не выполнялась. Проверить вручную по видео.</AlertDescription>
        </Alert>
      )}
      {it.vnote && (
        <Alert className="border-warning-border bg-warning-bg text-warning">
          <Eye />
          <AlertDescription className="text-[12px] text-warning">{it.vnote}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-2.5 rounded-2xl bg-muted p-3">
        <div className="flex items-center justify-between text-[12px] font-semibold uppercase tracking-[0.12em] text-slate"><span>Источник нормы</span><span className="font-normal normal-case tracking-normal">rules.json v0.4</span></div>
        {T.citations.length ? T.citations.map((c, k) => <RuleCiteBlock key={k} c={c} />) : (
          <div className="rounded-lg border bg-card p-3" data-testid="derived">
            <Badge variant="outline" className="rounded-full border-destructive/30 bg-danger-bg text-destructive">нормы нет — по rules.json</Badge>
            <p className="mt-2 text-[12px] text-muted-foreground">Цитата не выводится. Номер пункта не подставляется наугад.</p>
          </div>
        )}
        {T.note && <div className="rounded-md border border-warning-border/60 bg-warning-bg/60 px-2.5 py-1.5 text-[11.5px] leading-snug text-warning" data-testid="caveat"><b>rules.json:</b> {T.note}</div>}
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <div className="rounded-xl border p-3"><div className="flex items-center gap-1.5 text-[12.5px] font-semibold"><Eye className="size-3.5 text-sky" />Визуальный признак</div><p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{it.visual}</p></div>
        <div className="rounded-xl border border-dashed border-warning-border p-3" data-testid="cannot"><div className="flex items-center gap-1.5 text-[12.5px] font-semibold"><EyeOff className="size-3.5 text-amber" />Что нельзя утверждать по видео</div><p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{it.cannot}</p></div>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <Button size="lg" variant={cOn ? "default" : "outline"} className={cn(!cOn && "border-primary text-primary hover:text-primary dark:border-white/30 dark:text-foreground")} onClick={() => onStatus(it.id, "confirmed")} data-testid="confirm"><Check />{cOn ? "Подтверждено" : "Подтвердить"}</Button>
        <Button size="lg" variant={rOn ? "secondary" : "outline"} onClick={() => onStatus(it.id, "rejected")} data-testid="reject"><X />{rOn ? "Отклонено" : "Отклонить"}</Button>
      </div>
      <p className="text-center text-[11.5px] text-muted-foreground">{cOn || rOn ? "Нажмите ещё раз, чтобы вернуть «на проверке»" : "Решение оператора попадёт в JSON и в разметку"}</p>
    </CardContent></Card>
  )
}
