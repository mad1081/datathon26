import { Check, X, ExternalLink, Eye, ShieldAlert, ShieldCheck, ShieldQuestion, CircleSlash, Quote } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { ZONE_BY_KEY, fmt, isViolation, type Gap, type Item, type Scenario } from "@/lib/data"
import { BASELINE, CATEGORIES, SESSIONS, STEPS, STRENGTH, OUTSIDE_VERDICT, typeOf, type SessionKey } from "@/lib/baseline"
import { RULE_ACTS, type RuleCite } from "@/lib/rules"
import { TypeBadge } from "./Clause"

/* статус привязки к норме — по мотивам «Failing» в compliance-обзорах */
function normStatus(it: Item) {
  if (it.status === "rejected") return { label: "отклонено оператором", cls: "bg-muted text-muted-foreground", Icon: CircleSlash }
  if (it.status === "confirmed") return { label: "нарушение подтверждено", cls: "bg-destructive text-white border-transparent", Icon: ShieldAlert }
  if (isViolation(it)) return { label: "признаки нарушения", cls: "bg-danger-bg text-destructive border-destructive/30", Icon: ShieldAlert }
  return { label: "требует проверки", cls: "bg-warning-bg text-warning border-warning-border", Icon: ShieldQuestion }
}

function RuleCiteBlock({ c, it }: { c: RuleCite; it: Item }) {
  const a = RULE_ACTS[c.act]
  const st = normStatus(it)
  return (
    <div className="rounded-lg border bg-card p-3" data-testid="cite">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <a href={c.url} target="_blank" rel="noopener" className="group inline-flex items-center gap-1 text-[12.5px] font-semibold hover:text-primary">
            {a?.short ?? c.act}, {c.clause}<ExternalLink className="size-3 opacity-60 group-hover:opacity-100" />
          </a>
          <div className="text-[11px] text-muted-foreground">{a?.number}</div>
        </div>
        <Badge variant="outline" className={cn("shrink-0 gap-1 rounded-full text-[10.5px]", st.cls)}><st.Icon className="size-3" />{st.label}</Badge>
      </div>
      <div className="mt-2 flex gap-2 text-[12.5px] italic leading-relaxed">
        <Quote className="mt-0.5 size-3.5 shrink-0 text-primary" /><span>{c.quote}</span>
      </div>
      <Badge variant="outline" className="mt-2 gap-1 rounded-full border-success/30 bg-success-bg text-[10.5px] text-success">
        <ShieldCheck className="size-3" />из research/rules.json · {c.url.split("#")[1] ? "#" + c.url.split("#")[1] : "без якоря"}
      </Badge>
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
}

export function Detail({ S, item, gap, onGoto, onStatus, onStep }: Props) {
  if (gap) return (
    <Card><CardContent className="space-y-3">
      <div className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">не проанализировано</div>
      <div className="text-xl font-bold leading-tight">Отрезок {fmt(gap.a)}–{fmt(gap.b)}</div>
      <p className="text-[13.5px]">Модель не смотрела этот кусок: {gap.why}. Нарушение внутри него не исключено — просмотрите видео вручную. В ответе API отрезок лежит в <code className="font-mono text-xs">unanalyzed_ranges</code>.</p>
      <Badge variant="outline" className="rounded-full border-warning-border bg-warning-bg text-warning">Вердикт по этому отрезку не выносится</Badge>
    </CardContent></Card>
  )
  if (!item) return (
    <Card><CardContent className="space-y-2">
      <div className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">итог</div>
      <div className="text-xl font-bold">Нарушений не обнаружено</div>
      <ul className="divide-y text-[13px]">
        {[`Проанализировано 100% видео (${fmt(S.dur)})`, "Нарушений выше порога правил: 0", "Моментов ниже порога и от VLM: 0", "Непроанализированных отрезков: 0"].map((t) => (
          <li key={t} className="flex items-center gap-2 py-1.5"><Check className="size-4 text-success" />{t}</li>
        ))}
      </ul>
      <p className="text-[12.5px] text-muted-foreground">Пороги правил — из rules.json (0,60–0,85). В центре — кадры-выборка из видео.</p>
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
  return (
    <Card data-testid="detail"><CardContent className="space-y-3">
      <div>
        <div className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">{kick}</div>
        <div className="mt-1 text-xl font-bold leading-tight" data-testid="detail-type">{T.name_ru}</div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">{it.title} · <code className="font-mono text-[11px]">type_id: {it.tid}</code></div>
        <button className="mt-1 text-[12.5px] text-primary hover:underline" onClick={() => onGoto(it.tc)}>Перейти к {fmt(it.tc)}{win}</button>
        <div className="mt-2 flex flex-wrap items-center gap-1.5" data-testid="type-row">
          <TypeBadge tid={it.tid} compact />
          <span className="flex items-center gap-1 rounded-full border px-1.5 py-px text-[10.5px]" style={{ borderColor: cat.color + "66", color: cat.color }}><i className="size-1.5 rounded-full" style={{ background: cat.color }} />{cat.label}</span>
          <span className={cn("rounded-full px-1.5 py-px text-[10.5px]", STRENGTH[T.strength].cls)}>{STRENGTH[T.strength].label}</span>
          {!T.count_in_verdict && <span className="rounded-full bg-warning-bg px-1.5 py-px text-[10.5px] text-warning ring-1 ring-warning-border" data-testid="outside-verdict">{OUTSIDE_VERDICT}</span>}
          <span className="font-mono text-[10.5px] text-muted-foreground">порог {T.threshold}</span>
        </div>
        {sk && step ? (
          <button onClick={() => onStep(sk, step)} data-testid="goto-step"
            className="mt-2 flex w-full items-start gap-2 rounded-lg border border-dashed px-2.5 py-1.5 text-left text-[12px] hover:border-primary hover:bg-accent/50">
            <span className="min-w-0 flex-1"><span className="block text-[10.5px] uppercase tracking-[0.06em] text-muted-foreground">отклонение от эталона</span><b>{SESSIONS.find((x) => x.key === sk)!.label}</b> · шаг {stepN} «{STEPS[step].title}»</span>
            <span className="shrink-0 text-primary">→</span>
          </button>
        ) : (
          <div className="mt-2 rounded-lg border border-dashed px-2.5 py-1.5 text-[12px] text-muted-foreground" data-testid="goto-step">вне эталона — тип не привязан к шагу процедуры</div>
        )}
      </div>
      <p className="text-[13.5px] leading-relaxed">{it.desc}{it.demoConf && <span className="text-muted-foreground"> Уверенность {Math.round(it.conf * 100)}% — демо-значение.</span>}</p>
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

      <div className="space-y-2.5 rounded-xl bg-muted/70 p-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">Норма</div>
        {T.citations.length ? T.citations.map((c, k) => <RuleCiteBlock key={k} c={c} it={it} />) : (
          <div className="rounded-lg border bg-card p-3" data-testid="derived">
            <Badge variant="outline" className="rounded-full border-destructive/30 bg-danger-bg text-destructive">нормы нет — по rules.json</Badge>
            <p className="mt-2 text-[12px] text-muted-foreground">Цитата не выводится. Номер пункта не подставляется наугад.</p>
          </div>
        )}
        {T.note && <div className="rounded-md border border-warning-border/60 bg-warning-bg/60 px-2.5 py-1.5 text-[11.5px] leading-snug text-warning" data-testid="caveat"><b>rules.json:</b> {T.note}</div>}
        <Separator />
        <div className="grid grid-cols-2 gap-3">
          <div><div className="text-[12.5px] font-semibold">Визуальный признак</div><p className="mt-0.5 text-[12px] text-muted-foreground">{it.visual}</p></div>
          <div><div className="text-[12.5px] font-semibold">Нельзя утверждать по видео</div><p className="mt-0.5 text-[12px] text-muted-foreground">{it.cannot}</p></div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <Button variant={cOn ? "default" : "outline"} className={cn("h-10", !cOn && "border-primary/60 text-primary hover:text-primary")} onClick={() => onStatus(it.id, "confirmed")} data-testid="confirm"><Check />{cOn ? "Подтверждено" : "Подтвердить"}</Button>
        <Button variant={rOn ? "secondary" : "ghost"} className="h-10" onClick={() => onStatus(it.id, "rejected")} data-testid="reject"><X />{rOn ? "Отклонено" : "Отклонить"}</Button>
      </div>
      <p className="text-center text-[11.5px] text-muted-foreground">{cOn || rOn ? "Нажмите ещё раз, чтобы вернуть «на проверке»" : "Решение оператора попадёт в JSON и в разметку"}</p>
    </CardContent></Card>
  )
}
