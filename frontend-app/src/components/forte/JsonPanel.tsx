import { useMemo } from "react"
import { Copy, Download, Tags, Terminal } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AGREED_EXTRAS, CURL, PROPOSED_EXTRAS } from "@/lib/data"

const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]!)
function highlight(json: string) {
  return json.split("\n").map((ln) => esc(ln)
    .replace(/^(\s*)"([^"]*?)":/, '$1<span class="text-[#F6B6C9]">"$2"</span>:')
    .replace(/: "(.*)"(,?)$/, (_m, a: string, c: string) => ': <span class="text-[#F7DDB0]">"' + a.replace(/…\((\d+) KB\)/, '<span class="text-[#b58a9c]">…($1 KB)</span>') + '"</span>' + c)
    .replace(/: (\[?-?\d+\.?\d*(?:, -?\d+\.?\d*\])?)(,?)$/, ': <span class="text-[#A8E6C9]">$1</span>$2')
    .replace(/: (null|true|false)(,?)$/, ': <span class="text-[#9CC3FF]">$1</span>$2')).join("\n")
}
async function copy(text: string, msg: string) {
  try { await navigator.clipboard.writeText(text) } catch {
    const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove()
  }
  toast.success(msg)
}
function download(name: string, obj: unknown) {
  const a = document.createElement("a")
  a.href = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" }))
  a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

export function JsonPanel({ result, labels, file }: { result: unknown; labels: unknown[]; file: string }) {
  const text = useMemo(() => JSON.stringify(result, null, 2).replace(/\[\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]/g, "[$1, $2]"), [result])
  const html = useMemo(() => highlight(text), [text])
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="text-base">Ответ API (JSON)</CardTitle>
        <CardDescription>Отклонённые оператором нарушения <b>остаются</b> в ответе с <code className="font-mono text-xs">"operator_status": "rejected_by_operator"</code> и не влияют на <code className="font-mono text-xs">verdict</code> — ошибка оператора не спрячет настоящее нарушение. Решения копятся в разметку для дообучения.</CardDescription>
        <div className="col-span-full mt-1 flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => copy(JSON.stringify(result, null, 2), "JSON скопирован (base64 в демо сокращён)")} data-testid="copy"><Copy />Копировать</Button>
          <Button variant="outline" size="sm" onClick={() => download("result.json", result)}><Download />result.json</Button>
          <Button size="sm" onClick={() => labels.length ? download(`labels_${file.replace(/\.\w+$/, "")}.json`, labels) : toast.info("Разметка пуста: подтвердите или отклоните момент")} data-testid="labels"><Tags />Разметка ({labels.length})</Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="json">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <TabsList>
              <TabsTrigger value="json">result.json</TabsTrigger>
              <TabsTrigger value="curl"><Terminal />curl</TabsTrigger>
            </TabsList>
            <div className="flex flex-wrap gap-1.5 font-mono text-[11.5px]">
              <span className="rounded-md border bg-card px-2 py-0.5"><b className="text-primary">POST</b> /api/v1/analyze</span>
              <span className="rounded-md border bg-card px-2 py-0.5"><b className="text-primary">GET</b> /api/v1/jobs/{"{job_id}"}</span>
              <span className="rounded-md border bg-card px-2 py-0.5">заголовок <b className="text-primary">X-API-Key</b></span>
            </div>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => copy(CURL, "curl скопирован")} data-testid="curl"><Terminal />Скопировать curl</Button>
          </div>
          <div className="mb-2 rounded-lg border bg-muted/50 p-2.5 text-[11.5px] leading-relaxed" data-testid="extras-note">
            <div><span className="font-semibold">Обязательно для жюри (первыми, без изменений):</span> <code className="font-mono">job_id, status, verdict (violation | no_violation), violations[type, timecode_sec, description, evidence_frames{"{timestamp_sec, image_base64}"}]</code>. <code className="font-mono">type</code> = код из таксономии (V-ABSENT…).</div>
            <div className="mt-1 flex flex-wrap items-center gap-1"><span className="text-muted-foreground">extras согласованы с бэкендом:</span>{AGREED_EXTRAS.map((x) => <code key={x} className="rounded bg-success-bg px-1 font-mono text-[10.5px] text-success">{x}</code>)}</div>
            <div className="mt-1 flex flex-wrap items-center gap-1"><span className="text-muted-foreground">нужно согласовать:</span>{PROPOSED_EXTRAS.map((x) => <code key={x} className="rounded border border-dashed border-warning-border bg-warning-bg px-1 font-mono text-[10.5px] text-warning">{x}</code>)}</div>
          </div>
          <TabsContent value="json">
            <pre data-testid="json" className="max-h-[520px] overflow-auto rounded-xl bg-[#2A0A1A] p-4 font-mono text-[12px] leading-relaxed text-[#f2e6eb] dark:bg-[#0A0D12] dark:ring-1 dark:ring-white/10" dangerouslySetInnerHTML={{ __html: html }} />
          </TabsContent>
          <TabsContent value="curl">
            <pre className="overflow-auto rounded-xl bg-[#2A0A1A] p-4 font-mono text-[12px] leading-relaxed text-[#f2e6eb] dark:bg-[#0A0D12]">{CURL}</pre>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
