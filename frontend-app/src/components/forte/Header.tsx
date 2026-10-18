import { Moon, Sun, Upload, LayoutPanelTop } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { ForteLogo } from "./ForteLogo"
import type { ScenarioKey } from "@/lib/data"

type Props = {
  screen: "result" | "upload"
  onScreen: (s: "result" | "upload") => void
  scenario: ScenarioKey
  onScenario: (s: ScenarioKey) => void
  dark: boolean
  onDark: (d: boolean) => void
  fileName: string
}

const SC: { k: ScenarioKey; label: string; dot: string }[] = [
  { k: "real", label: "Реальное видео", dot: "bg-success" },
  { k: "demo_viol", label: "Демо: нарушения", dot: "bg-destructive" },
  { k: "demo_clean", label: "Демо: чисто", dot: "bg-success/60" },
]

/* top-nav по бренд-буку: app-icon tile (магента), вордмарк, underline-табы с магентовой чертой, segmented-toggle «вино/контур» */
export function Header({ screen, onScreen, scenario, onScenario, dark, onDark, fileName }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b bg-card/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-4 px-6 max-[1360px]:px-4">
        <div className="flex items-center gap-3 select-none">
          <ForteLogo className="h-7 w-auto text-brand dark:text-white" />
          <div className="border-l border-hairline pl-3 text-[11px] font-semibold uppercase leading-tight tracking-[0.14em] text-slate">кассовый<br />контроль</div>
        </div>

        <nav className="ml-4 flex h-full items-stretch gap-5" aria-label="Экран">
          {([["upload", "Загрузка", Upload], ["result", "Результат", LayoutPanelTop]] as const).map(([k, label, Icon]) => (
            <button key={k} onClick={() => onScreen(k)} data-testid={"nav-" + k} aria-current={screen === k}
              className={cn("relative flex items-center gap-1.5 text-[15px] font-medium transition-colors ease-forte",
                screen === k ? "text-foreground" : "text-muted-foreground hover:text-foreground")}>
              <Icon className="size-4" />{label}
              <span className={cn("absolute inset-x-0 bottom-0 h-0.5 rounded-full transition-opacity", screen === k ? "bg-brand opacity-100" : "opacity-0")} />
            </button>
          ))}
        </nav>

        <div className="flex-1" />

        <div className="flex items-center gap-1.5" role="radiogroup" aria-label="Сценарий">
          {SC.map((s) => {
            const on = scenario === s.k && screen === "result"
            return (
              <button key={s.k} role="radio" aria-checked={on} data-testid={"sc-" + s.k} onClick={() => onScenario(s.k)}
                className={cn("flex h-9 items-center gap-2 rounded-lg border px-3 text-[13.5px] font-medium transition-colors ease-forte max-[1360px]:px-2.5 max-[1360px]:text-[13px]",
                  on ? "border-transparent bg-primary text-primary-foreground" : "border-primary/70 text-primary hover:bg-accent dark:border-white/20 dark:text-foreground")}>
                <span className={cn("size-2 rounded-full", s.dot, on && "ring-2 ring-white/70")} />{s.label}
              </button>
            )
          })}
        </div>

        <span className="hidden max-w-[150px] truncate font-mono text-xs text-muted-foreground 2xl:inline">{fileName}</span>
        <Tooltip>
          <TooltipTrigger asChild>
            <button onClick={() => onDark(!dark)} aria-label="Тема" data-testid="theme"
              className="grid size-10 place-items-center rounded-full border bg-card text-muted-foreground transition-colors hover:text-foreground">
              {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
          </TooltipTrigger>
          <TooltipContent>{dark ? "Светлая тема" : "Тёмная тема"}</TooltipContent>
        </Tooltip>
      </div>
    </header>
  )
}
