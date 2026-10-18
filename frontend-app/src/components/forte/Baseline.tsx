import { Check, X, Minus, AlertTriangle, CircleDashed, EyeOff, ListChecks, BookOpen, ScanSearch } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { BASELINE, SESSIONS, SESSION_BY_KEY, STEPS, type SessionKey } from "@/lib/baseline"
import { compliance, effStatus, fmt, stepResult, type Item, type ProcStatus, type Scenario } from "@/lib/data"
import { ClauseChip, TypeBadge, Unverified } from "./Clause"

export const PST: Record<ProcStatus, { label: string; cls: string; Icon: typeof Check }> = {
  done: { label: "выполнен", cls: "bg-success text-white", Icon: Check },
  missed: { label: "отклонение", cls: "bg-destructive text-white", Icon: X },
  na: { label: "не применимо", cls: "bg-muted text-muted-foreground ring-1 ring-border", Icon: Minus },
  manual: { label: "проверить вручную", cls: "bg-warning-bg text-warning ring-1 ring-warning-border", Icon: AlertTriangle },
  not_visible: { label: "не видно на камере", cls: "border border-dashed border-muted-foreground/50 bg-card text-muted-foreground", Icon: CircleDashed },
  off: { label: "вне видео", cls: "bg-muted text-muted-foreground/70", Icon: EyeOff },
}

type Props = { S: Scenario; items: Item[]; tab: SessionKey; onTab: (k: SessionKey) => void; onItem: (id: string) => void; onSeek: (t: number) => void; onTaxonomy: () => void }

/* «Эталон процедуры»: сравнение сессии с эталонной цепочкой шагов по Правилам №231 */
export function Baseline({ S, items, tab, onTab, onItem, onSeek, onTaxonomy }: Props) {
  const detected = S.sessions.map((s) => s.type)
  const hit = S.sessions.find((s) => s.type === tab)
  const c = compliance(S, tab, items)
  const pct = c.total ? Math.round((c.ok / c.total) * 100) : 0
  return (
    <Card className="gap-0 py-0" data-testid="baseline">
      <div className="flex items-center gap-2 px-4 pt-3">
        <ListChecks className="size-4 text-primary" />
        <span className="text-[17px] font-semibold">Эталон процедуры</span>
        <span className="text-[11px] text-muted-foreground">Правила №231</span>
        <Button variant="ghost" size="sm" className="ml-auto h-7 gap-1 px-2 text-[12px]" onClick={onTaxonomy} data-testid="open-taxonomy"><BookOpen className="size-3.5" />Типы нарушений</Button>
      </div>

      {/* определённый тип сессии */}
      <div className="px-4 pt-1.5" data-testid="session-detect">
        {S.sessions.length ? (
          <div className="flex flex-wrap items-center gap-1.5 text-[12px]">
            <ScanSearch className="size-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">определено:</span>
            {S.sessions.map((s) => (
              <button key={s.type} onClick={() => { onTab(s.type); onSeek(s.a) }}
                className="rounded-full bg-accent px-2 py-0.5 font-semibold text-primary hover:brightness-95">
                {SESSION_BY_KEY[s.type].label} <span className="font-mono text-[10.5px] font-normal opacity-80">{fmt(s.a)}–{fmt(s.b)} · {Math.round(s.conf * 100)}%</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-1.5 rounded-md border border-warning-border bg-warning-bg px-2 py-1 text-[12px] text-warning"><AlertTriangle className="size-3.5" />тип не определён — проверить вручную</div>
        )}
        {S.sessionNote && <div className="mt-0.5 text-[10.5px] text-muted-foreground">{S.sessionNote}</div>}
      </div>

      {/* сегментированный выбор типа сессии */}
      <div className="mx-4 mt-3 flex flex-wrap gap-2" role="tablist">
        {SESSIONS.map((s) => {
          const on = tab === s.key, det = detected.includes(s.key)
          return (
            <button key={s.key} role="tab" aria-selected={on} data-testid={"tab-" + s.key} data-detected={det} onClick={() => onTab(s.key)} title={s.hint}
              className={cn("relative flex h-9 items-center justify-center gap-1.5 rounded-lg border px-3 text-[13.5px] font-medium transition-colors ease-forte",
                on ? "border-transparent bg-primary text-primary-foreground" : det ? "border-primary text-primary hover:bg-accent dark:border-white/40 dark:text-foreground" : "border-hairline text-muted-foreground hover:bg-accent")}>
              {det && <span className={cn("size-2 rounded-full", on ? "bg-sky" : "bg-brand")} />}{s.label}{det && <span className={cn("text-[10.5px] font-normal", on ? "text-white/75" : "text-muted-foreground")}>определено</span>}
            </button>
          )
        })}
      </div>

      {/* счёт соответствия */}
      <div className="px-4 pb-1 pt-2.5" data-testid="compliance">
        {hit ? (
          <>
            <div className="flex items-baseline gap-2">
              <span className="text-[15px] font-bold">Соответствие {c.ok}/{c.total} {c.total === 1 ? "шага" : "шагов"}</span>
              <span className="font-mono text-[11px] text-muted-foreground tabular">{pct}%</span>
              <span className="ml-auto text-[11px] text-muted-foreground">{c.manual ? <span className="text-warning">! {c.manual} вручную · </span> : null}{c.off} вне видео</span>
            </div>
            <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
              <div className={cn("h-full rounded-full transition-all", pct === 100 ? "bg-success" : pct >= 50 ? "bg-warning" : "bg-destructive")} style={{ width: `${pct}%` }} />
            </div>
            <div className="mt-1 text-[10.5px] text-muted-foreground">считаются только шаги, видимые на камере; «вне видео» и «не применимо» — не в счёт</div>
          </>
        ) : (
          <div className="rounded-md bg-muted/70 px-2.5 py-1.5 text-[11.5px] text-muted-foreground">В этом видео сессия «{SESSION_BY_KEY[tab].label}» не обнаружена — показан эталон ({SESSION_BY_KEY[tab].hint}).</div>
        )}
      </div>

      <CardContent className="px-2 pb-2 pt-0">
        <ol>
          {BASELINE[tab].map((id, i) => {
            const st = STEPS[id], r = stepResult(S, tab, id)
            const es = r ? effStatus(r, items) : null
            const p = es ? PST[es] : null
            const linked = (r?.links ?? []).map((x) => items.find((y) => y.id === x)).filter(Boolean) as Item[]
            const click = () => { if (linked.length) onItem(linked[0].id); else if (r?.tc !== undefined) onSeek(r.tc) }
            const off = st.obs === "off"
            return (
              <li key={id} data-step={id} data-status={es ?? "baseline"}>
                <div role="button" tabIndex={0} onClick={click} onKeyDown={(e) => e.key === "Enter" && click()}
                  className={cn("group flex items-start gap-2.5 rounded-md px-2 py-1.5", (linked.length || r?.tc !== undefined) ? "cursor-pointer hover:bg-muted/70" : "cursor-default", off && "opacity-60", es === "missed" && "bg-danger-bg/60")}>
                  {p ? <span className={cn("mt-0.5 grid size-[18px] shrink-0 place-items-center rounded-full", p.cls)} title={p.label}><p.Icon className="size-3" strokeWidth={3} /></span>
                    : <span className="mt-0.5 grid size-[18px] shrink-0 place-items-center rounded-full border text-[10px] text-muted-foreground">{i + 1}</span>}
                  <div className="min-w-0 flex-1">
                    <div className="text-[12.5px] font-medium leading-snug">{st.title}{id === "all.personal" && tab !== "start_end" && <span className="ml-1 text-[10.5px] font-normal text-muted-foreground">· весь день</span>}</div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px] text-muted-foreground">
                      {st.cites.map((k) => <ClauseChip key={k} k={k} />)}
                      {st.internal && <><span className="rounded border px-1 font-mono text-[10px]">внутр.</span><Unverified text={st.internal} /></>}
                      {off ? <span className="rounded bg-muted px-1 text-[10px]">вне видео</span> : <span className="rounded px-1 text-[10px] ring-1 ring-border">видно на камере</span>}
                      {p && !off && <span className={cn(es === "missed" && "font-medium text-destructive", es === "manual" && "text-warning")}>{p.label}</span>}
                      {linked.map((it) => <TypeBadge key={it.id} tid={it.tid} compact onClick={() => onItem(it.id)} className={it.status === "rejected" ? "line-through opacity-50" : ""} />)}
                    </div>
                    {r && !off && r.note && <div className="mt-0.5 text-[11px] leading-snug text-muted-foreground">{r.note}</div>}
                    {!r && st.how && <div className="mt-0.5 text-[11px] leading-snug text-muted-foreground">{st.how}</div>}
                  </div>
                  {r?.tc !== undefined && !off && <span className="mt-0.5 shrink-0 font-mono text-[11px] text-muted-foreground tabular group-hover:text-primary">{fmt(r.tc)}</span>}
                </div>
              </li>
            )
          })}
        </ol>
        <div className="flex flex-wrap gap-x-2.5 gap-y-0.5 px-2 pt-1.5 text-[10.5px] text-muted-foreground">
          {(["done", "missed", "na", "manual", "not_visible", "off"] as ProcStatus[]).map((k) => {
            const P = PST[k]
            return <span key={k} className="flex items-center gap-1"><span className={cn("grid size-3 place-items-center rounded-full", P.cls)}><P.Icon className="size-2" strokeWidth={3} /></span>{P.label}</span>
          })}
        </div>
        <div className="px-2 pt-1 text-[10.5px] text-muted-foreground">Цитаты — по наведению на пункт; все якоря сверены с локальной копией adilet.zan.kz. Клик по шагу — к моменту или к нарушению.</div>
      </CardContent>
    </Card>
  )
}
