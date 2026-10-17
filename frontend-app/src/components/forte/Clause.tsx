import { ExternalLink, ShieldQuestion } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { ADILET, CITES, citeUrl } from "@/lib/norms"
import { CATEGORIES, typeOf } from "@/lib/baseline"
import { RULE_ACTS, type RuleCite } from "@/lib/rules"

/* чип пункта: ссылка на adilet с якорем, цитата по наведению */
export function ClauseChip({ k, className }: { k: string; className?: string }) {
  const c = CITES[k], a = ADILET[c.act]
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <a href={citeUrl(k)} target="_blank" rel="noopener" onClick={(e) => e.stopPropagation()} data-clause={k}
          className={cn("inline-flex items-center gap-0.5 rounded border bg-card px-1 font-mono text-[10px] text-muted-foreground hover:border-primary hover:text-primary", className)}>
          {c.act !== "R231" && <span className="opacity-70">№{c.act.slice(1)}·</span>}{c.clause}<ExternalLink className="size-2.5" />
        </a>
      </TooltipTrigger>
      <TooltipContent className="max-w-[320px] text-[11.5px] leading-snug">
        <div className="mb-1 font-semibold not-italic">{a.short}, {c.clause}</div>
        <div className="italic">«{c.parts.map((p) => p.text).join(" ")}»</div>
        <div className="mt-1 opacity-70">дословно · adilet #{c.parts.map((p) => p.z).join(", #")} · сверено с локальной копией</div>
      </TooltipContent>
    </Tooltip>
  )
}

export function Unverified({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center gap-0.5 rounded border border-dashed border-warning-border bg-warning-bg px-1 text-[10px] text-warning" data-testid="unverified">
          <ShieldQuestion className="size-2.5" />не сверено
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-[280px] text-[11.5px]">{text}. Номер пункта не подставляется наугад.</TooltipContent>
    </Tooltip>
  )
}

/* бейдж типа: name_ru + ключ rules.json (type_id) мелким моноширинным; compact — только ключ */
export function TypeBadge({ tid, compact, className, onClick }: { tid: string; compact?: boolean; className?: string; onClick?: () => void }) {
  const t = typeOf(tid), c = CATEGORIES[t.cat].color
  const El = onClick ? "button" : "span"
  return (
    <El onClick={onClick ? (e: React.MouseEvent) => { e.stopPropagation(); onClick() } : undefined} title={`${t.name_ru} · type_id: ${tid}`} data-type-id={tid}
      className={cn("inline-flex min-w-0 max-w-full items-baseline gap-1 rounded px-1 py-px text-left leading-tight", onClick && "hover:brightness-95", className)}
      style={{ background: c + "1A", boxShadow: `inset 0 0 0 1px ${c}55` }}>
      {!compact && <span className="truncate text-[11px] font-semibold" style={{ color: c }}>{t.name_ru}</span>}
      <span className={cn("shrink-0 font-mono text-[9.5px]", compact ? "font-semibold" : "opacity-70")} style={{ color: c }}>{tid}</span>
    </El>
  )
}

/* цитата из rules.json (правило несёт свои нормы) */
export function RuleCiteChip({ c }: { c: RuleCite }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <a href={c.url} target="_blank" rel="noopener" onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-0.5 rounded border bg-card px-1 font-mono text-[10px] text-muted-foreground hover:border-primary hover:text-primary">
          {c.act !== "R231" && <span className="opacity-70">{RULE_ACTS[c.act]?.short.replace("Правила ", "").replace("Инструкция ", "") ?? c.act}·</span>}{c.clause}<ExternalLink className="size-2.5" />
        </a>
      </TooltipTrigger>
      <TooltipContent className="max-w-[320px] text-[11.5px] leading-snug">
        <div className="mb-1 font-semibold">{RULE_ACTS[c.act]?.short}, {c.clause}</div>
        <div className="italic">«{c.quote}»</div>
        <div className="mt-1 opacity-70">из research/rules.json</div>
      </TooltipContent>
    </Tooltip>
  )
}
