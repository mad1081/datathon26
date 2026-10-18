import type { ReactNode } from "react"
import { BookOpen, Braces, ListChecks } from "lucide-react"
import { cn } from "@/lib/utils"
import { RULES } from "@/lib/rules"

type Tab = "baseline" | "json"
/* Вторичные подробности — за underline-табами (бренд-бук: активный таб — винный текст + черта sky-blue) */
export function MoreDetails({ tab, onTab, baseline, json, comp, onTaxonomy }: { tab: Tab; onTab: (t: Tab) => void; baseline: ReactNode; json: ReactNode; comp: { ok: number; total: number } | null; onTaxonomy: () => void }) {
  const T: { k: Tab; label: string; Icon: typeof Braces; sub?: string }[] = [
    { k: "baseline", label: "Эталон процедуры", Icon: ListChecks, sub: comp ? `${comp.ok}/${comp.total}` : undefined },
    { k: "json", label: "Ответ API (JSON)", Icon: Braces },
  ]
  return (
    <section data-testid="more" className="flex flex-col gap-4">
      <div className="flex items-end gap-7 border-b-2 border-surface-gray">
        <h2 className="mb-2 mr-2 text-[20px] font-semibold">Подробности</h2>
        {T.map(({ k, label, Icon, sub }) => (
          <button key={k} onClick={() => onTab(k)} data-testid={"more-" + k} aria-selected={tab === k} role="tab"
            className={cn("relative -mb-0.5 flex items-center gap-1.5 border-b-2 pb-2 text-[15px] font-medium leading-7 transition-colors ease-forte",
              tab === k ? "border-sky text-wine-deep" : "border-transparent text-slate hover:text-foreground")}>
            <Icon className="size-4" />{label}{sub && <span className="rounded-full bg-muted px-1.5 text-[11.5px] tabular">{sub}</span>}
          </button>
        ))}
        <button onClick={onTaxonomy} data-testid="open-taxonomy-2" className="relative -mb-0.5 flex items-center gap-1.5 border-b-2 border-transparent pb-2 text-[15px] font-medium leading-7 text-slate hover:text-foreground">
          <BookOpen className="size-4" />Типы нарушений ({RULES.length})
        </button>
      </div>
      <div className="fade-in" key={tab}>{tab === "baseline" ? baseline : json}</div>
    </section>
  )
}
