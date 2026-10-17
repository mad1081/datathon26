import { Moon, Sun, Upload, LayoutPanelTop, Camera } from "lucide-react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
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

export function Header({ screen, onScreen, scenario, onScenario, dark, onDark, fileName }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b bg-card/85 backdrop-blur-md">
      <div className="flex h-14 items-center gap-3 px-4">
        <div className="text-[28px] font-extrabold leading-none tracking-[-0.06em] text-primary select-none">forte</div>
        <Separator orientation="vertical" className="h-6!" />
        <div className="hidden xl:block text-[14px] font-semibold whitespace-nowrap">Контроль кассовых операций</div>
        <Badge variant="outline" className="hidden lg:inline-flex gap-1 text-muted-foreground"><Camera className="size-3" />CAM-01 · касса</Badge>

        <div className="flex-1" />

        <ToggleGroup type="single" variant="outline" size="sm" value={screen} onValueChange={(v) => v && onScreen(v as "result" | "upload")} aria-label="Экран">
          <ToggleGroupItem value="upload" className="gap-1.5 px-3" data-testid="nav-upload"><Upload className="size-3.5" />Загрузка</ToggleGroupItem>
          <ToggleGroupItem value="result" className="gap-1.5 px-3" data-testid="nav-result"><LayoutPanelTop className="size-3.5" />Результат</ToggleGroupItem>
        </ToggleGroup>

        <Separator orientation="vertical" className="h-6!" />
        <span className="text-xs text-muted-foreground whitespace-nowrap">сценарий</span>
        <ToggleGroup type="single" size="sm" value={scenario} onValueChange={(v) => v && onScenario(v as ScenarioKey)} className="rounded-lg bg-muted p-0.5" aria-label="Сценарий">
          <ToggleGroupItem value="real" data-testid="sc-real" className="gap-1.5 px-2.5 data-[state=on]:bg-card data-[state=on]:shadow-sm"><span className="size-2 rounded-full bg-success" />реальное видео</ToggleGroupItem>
          <ToggleGroupItem value="demo_viol" data-testid="sc-demo_viol" className="gap-1.5 px-2.5 data-[state=on]:bg-card data-[state=on]:shadow-sm"><span className="size-2 rounded-full bg-destructive" />демо: нарушения</ToggleGroupItem>
          <ToggleGroupItem value="demo_clean" data-testid="sc-demo_clean" className="gap-1.5 px-2.5 data-[state=on]:bg-card data-[state=on]:shadow-sm"><span className="size-2 rounded-full bg-success/50" />демо: чисто</ToggleGroupItem>
        </ToggleGroup>

        <Separator orientation="vertical" className="h-6!" />
        <span className="hidden 2xl:inline font-mono text-xs text-muted-foreground">{fileName}</span>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" size="icon-sm" onClick={() => onDark(!dark)} aria-label="Тема" data-testid="theme">
              {dark ? <Sun /> : <Moon />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{dark ? "Светлая тема" : "Тёмная тема"}</TooltipContent>
        </Tooltip>
      </div>
    </header>
  )
}
