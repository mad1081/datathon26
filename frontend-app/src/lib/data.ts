/* Данные демо. Нормы — дословно из локальной копии adilet.zan.kz (см. norms.ts).
   Iteration 5: соответствие эталону процедуры + таксономия нарушений (baseline.ts). */
import { ADILET, CITES, citeUrl, PRE_VERIFIED } from "./norms"
import { BASELINE, CATEGORIES, SESSIONS, STEPS, typeOf, type SessionKey } from "./baseline"
import { RULE_ACTS, type RuleCite } from "./rules"
export { ADILET, CITES, citeUrl, PRE_VERIFIED }

export type Status = "pending" | "confirmed" | "rejected"
export type TrackKey =
  | "client_at_window" | "cashier_at_desk" | "cash_location" | "counting"
  | "second_employee" | "phone" | "document_card"
export type Region = "deskall" | "phone" | "card" | "device" | "desk" | "chair"
export type CashState = "hands" | "desk" | "counter" | "safe"
export type Seg = { a: number; b: number; label: string; soft?: boolean; state?: CashState }
export type ZoneKey = "safe" | "desk" | "counter" | "client"
export type Zone = { key: ZoneKey; label: string; short: string; color: string; polygon: [number, number][] }
export type Gap = { a: number; b: number; why: string }
export type Frame = { t: number; region: Region | null }
export type Item = {
  id: string
  tid: string             /* type_id = ключ research/rules.json; type = name_ru */
  step: string | null     /* шаг эталона, от которого отклонение; null → вне эталона */
  kind: "violation" | "observation"
  source: "rule" | "vlm"
  omission: boolean
  title: string
  short: string
  color: string           /* = цвет категории таксономии */
  tc: number
  iv: [number, number]
  conf: number
  thr: number | null
  rule: string | null
  status: Status
  demoConf?: boolean
  desc: string
  vnote?: string
  visual: string
  cannot: string
  frames: Frame[]
  mi?: number
  flab?: string[]
  zoneMissing?: ZoneKey
}
/* статусы шага: ✓ выполнен / ✕ отклонение / – не применимо / ! проверить вручную / ◌ не видно на камере / вне видео */
export type ProcStatus = "done" | "missed" | "na" | "manual" | "not_visible" | "off"
export type StepResult = { status: ProcStatus; tc?: number; links?: string[]; note: string }
export type SessionHit = { type: SessionKey; a: number; b: number; conf: number }
export type Phase = { n: number; label: string; st: "ok" | "dev" | "na" | "nv"; t?: number; iv?: [number, number]; note: string; link?: string; step?: string }
export type ScenarioKey = "real" | "demo_viol" | "demo_clean"
export type Scenario = {
  key: ScenarioKey
  label: string
  src: "real" | "demo"
  file: string
  job: string
  dur: number
  start: number
  sel: string | null
  tracks: Record<TrackKey, Seg[]>
  gaps: Gap[]
  items: Item[]
  sample?: number[]
  zonesFound: ZoneKey[]
  zoneNote?: string
  sessions: SessionHit[]           /* пусто → тип не определён */
  sessionNote?: string
  results: Partial<Record<SessionKey, Record<string, StepResult>>>
  phases: Phase[]
}

export const TRACKS: { key: TrackKey; label: string }[] = [
  { key: "client_at_window", label: "Клиент в помещении" },
  { key: "cashier_at_desk", label: "Кассир за столом" },
  { key: "cash_location", label: "Где деньги" },
  { key: "counting", label: "Пересчёт" },
  { key: "second_employee", label: "Второй сотрудник" },
  { key: "phone", label: "Телефон" },
  { key: "document_card", label: "Документ / карта" },
]

/* кадры извлечены ffmpeg из sample.mov; размер base64 в KB */
export const B64KB: Record<string, number> = { "0.5": 49, "1.0": 50, "2.0": 50, "3.0": 50, "4.0": 51, "5.0": 51, "6.0": 51, "7.5": 51, "8.4": 50, "9.0": 50, "10.0": 51, "11.0": 52, "12.0": 52, "13.0": 52, "14.0": 53, "14.6": 53, "15.5": 52, "16.2": 52, "16.5": 52 }
export const FRAME_TIMES = Object.keys(B64KB).map(Number).sort((a, b) => a - b)
export const IMG = (t: number) => `./video/f_${t.toFixed(1)}.jpg`
export const nearestFrame = (t: number) => FRAME_TIMES.reduce((p, c) => (Math.abs(c - t) < Math.abs(p - t) ? c : p), FRAME_TIMES[0])
export const VW = 464, VH = 848
export const REGIONS: Record<Region, [number, number, number, number]> = {
  deskall: [34, 384, 262, 92], phone: [150, 410, 70, 40], card: [140, 418, 42, 28],
  device: [32, 396, 88, 90], desk: [118, 404, 150, 76], chair: [168, 428, 150, 150],
}
export const DUR = 17.07

/* Зоны размечены вручную по кадру sample.mov (464×848), координаты нормированы 0..1.
   Только объекты и области — без лиц. */
export const ZONES: Zone[] = [
  { key: "safe", label: "сейф", short: "сейф", color: "#64748B",
    polygon: [[0.665, 0.44], [0.785, 0.424], [0.89, 0.452], [0.887, 0.556], [0.79, 0.585], [0.665, 0.552]] },
  { key: "desk", label: "стол / рабочее место", short: "стол", color: "#D08A1E",
    polygon: [[0.23, 0.487], [0.463, 0.462], [0.645, 0.505], [0.4, 0.565], [0.165, 0.632], [0.245, 0.575]] },
  { key: "counter", label: "счётная машинка", short: "машинка", color: "#2F6FD6",
    polygon: [[0.075, 0.505], [0.215, 0.49], [0.245, 0.562], [0.105, 0.585]] },
  { key: "client", label: "сторона клиента", short: "клиент", color: "#1F8A5B",
    polygon: [[0.0, 0.33], [0.36, 0.355], [0.5, 0.395], [0.465, 0.46], [0.07, 0.5], [0.0, 0.5]] },
]
export const ZONE_BY_KEY = Object.fromEntries(ZONES.map((z) => [z.key, z])) as Record<ZoneKey, Zone>
/* состояния дорожки «Где деньги»: цвета = цвета зон; «в руках» — акцент Forte */
export const CASH_STATES: Record<CashState, { label: string; color: string; zone: ZoneKey | null }> = {
  hands: { label: "в руках", color: "#9B1B4A", zone: null },
  desk: { label: "на столе", color: "#D08A1E", zone: "desk" },
  counter: { label: "в машинке", color: "#2F6FD6", zone: "counter" },
  safe: { label: "в сейфе", color: "#64748B", zone: "safe" },
}
const f = (t: number, region: Region | null = null): Frame => ({ t, region })
const empty = (): Record<TrackKey, Seg[]> => ({ client_at_window: [], cashier_at_desk: [], cash_location: [], counting: [], second_employee: [], phone: [], document_card: [] })

/* конструктор находки: цвет группы и шаг эталона по умолчанию — из таксономии rules.json */
type ItemIn = Omit<Item, "color" | "step"> & { step?: string | null }
const mk = (x: ItemIn): Item => {
  const t = typeOf(x.tid)
  return { ...x, step: x.step !== undefined ? x.step : t.steps[0] ?? null, color: CATEGORIES[t.cat].color }
}

export const SCENARIOS: Record<ScenarioKey, Scenario> = {
  real: {
    key: "real", label: "Реальное видео", src: "real", file: "sample.mov", job: "5b0e7c21a94d4f0f8e3a6c19d2b74e10", dur: DUR, start: 8.0, sel: "r1",
    tracks: { ...empty(),
      client_at_window: [{ a: 2.0, b: DUR, label: "входит → сидит у стола" }],
      cashier_at_desk: [{ a: 0, b: DUR, label: "кассир" }],
      phone: [{ a: 0, b: DUR, label: "на столе (по VLM, не подтверждено)", soft: true }],
      document_card: [{ a: 7.0, b: 15.0, label: "карта: передана → проверка → в устройство" }],
    },
    gaps: [], zonesFound: ["safe", "desk", "counter", "client"],
    sessions: [{ type: "cash_in", a: 2.0, b: DUR, conf: 0.55 }],
    sessionNote: "Тип — по передаче документа клиентом; наличных в кадре нет, уверенность низкая (демо-значение).",
    results: {
      cash_in: {
        "ci.id": { status: "done", tc: 7.5, note: "Клиент передаёт карту/документ (7–9 с). Тип документа по видео не определяется; лица не распознаются." },
        "ci.recount": { status: "na", note: "Наличных в кадре нет." },
        "ci.lock": { status: "na", note: "Наличных в кадре нет." },
        "ci.stay": { status: "done", tc: 2.0, note: "Кассир за столом весь ролик, клиент — с 2,0 с." },
        "all.personal": { status: "manual", tc: 0.5, links: ["r1"], note: "VLM видит телефон ниже порога — проверить вручную." },
      },
    },
    phases: [
      { n: 1, label: "клиент подошёл", st: "ok", t: 2.0, note: "клиент входит в 2,0 с" },
      { n: 2, label: "документ", st: "ok", t: 7.5, iv: [7.0, 9.0], note: "передача карты/документа 7–9 с", step: "ci.id" },
      { n: 3, label: "деньги приняты", st: "na", note: "наличных в кадре нет", step: "ci.recount" },
      { n: 4, label: "пересчёт", st: "na", note: "наличных в кадре нет", step: "ci.recount" },
      { n: 5, label: "в ящик", st: "na", note: "наличных в кадре нет", step: "ci.lock" },
      { n: 6, label: "клиент ушёл", st: "nv", note: "после конца ролика" },
    ],
    items: [mk({
      id: "r1", tid: "phone_or_personal_items", kind: "observation", source: "rule", omission: false, title: "Телефон на рабочем столе кассира", short: "Телефон на столе",
      tc: 0.5, iv: [0, DUR], conf: 0.41, thr: 0.6, rule: "phone_or_personal_items", status: "pending", demoConf: true,
      desc: "Видео-модель отмечает смартфон на столе кассира весь ролик. Кассир его не берёт, наличных в кадре нет — уверенность ниже порога правила (0,60), в нарушения не попало. Нужна ручная проверка.",
      vnote: "При ручном просмотре кадров смартфон на столе не найден (тёмный изгиб за ноутбуком — спинка кресла). Рамка обводит весь стол, а не телефон. Проверьте по исходному видео.",
      visual: "По VLM — смартфон на столе; кассир его не берёт. На кадрах видны ноутбук, чёрное устройство и карта клиента",
      cannot: "Что это личный смартфон с камерой, а не служебный телефон или связь без камеры (разрешено, п. 12 ч. 2); что комната — кассовый узел",
      frames: [f(0.5, "deskall"), f(8.4, "deskall"), f(16.5, "deskall")], mi: 0, flab: ["момент (начало)", "середина", "конец"],
    })],
  },
  demo_viol: {
    key: "demo_viol", label: "Демо: нарушения", src: "demo", file: "sample.mov", job: "3c639f53e0b74ab7a3f4609eb4caf05b", dur: DUR, start: 12.0, sel: "d3",
    tracks: { ...empty(),
      client_at_window: [{ a: 2.0, b: 14.2, label: "клиент" }],
      cashier_at_desk: [{ a: 0, b: 11.8, label: "кассир" }, { a: 13.6, b: DUR, label: "кассир" }],
      cash_location: [
        { a: 2.5, b: 3.2, label: "", state: "hands" }, { a: 3.2, b: 14.0, label: "на столе", state: "desk" },
        { a: 14.0, b: 14.6, label: "", state: "hands" }, { a: 14.6, b: DUR, label: "в машинке", state: "counter" }],
      counting: [{ a: 14.6, b: 15.8, label: "пересчёт (один)" }],
      second_employee: [{ a: 0, b: 1.4, label: "" }],
      phone: [{ a: 15.8, b: 16.8, label: "тел." }],
      document_card: [{ a: 2.2, b: 2.8, label: "" }],
    },
    gaps: [{ a: 5.0, b: 6.0, why: "окно пропущено при укрупнении (лимит времени)" }],
    zonesFound: ["desk", "counter", "client"],
    zoneNote: "Зона «сейф» в этом демо не распознана (перекрыта) — проверки хранения в сейфе переведены в ручные.",
    sessions: [{ type: "cash_in", a: 2.0, b: 14.2, conf: 0.88 }, { type: "no_client", a: 14.2, b: DUR, conf: 0.81 }],
    results: {
      cash_in: {
        "ci.id": { status: "done", tc: 2.4, note: "Передача документа видна (2,2–2,8 с); тип документа не определяется." },
        "ci.recount": { status: "missed", tc: 4.0, links: ["d1"], note: "Деньги приняты в 2,5 с и сразу легли на стол — пересчёта при клиенте нет." },
        "ci.lock": { status: "missed", tc: 12.4, links: ["d2", "d3", "d7"], note: "Деньги на столе 3,2–14,0 с, без кассира 11,8–13,6 с, у края со стороны клиента; сейф не распознан." },
        "ci.stay": { status: "missed", tc: 12.0, links: ["d3"], note: "Уход с места при клиенте 11,8–13,6 с." },
        "all.personal": { status: "manual", tc: 16.2, links: ["d6"], note: "VLM: телефон над деньгами 16,2 с." },
      },
      no_client: {
        "nc.control": { status: "missed", tc: 14.6, links: ["d5"], note: "Клиент ушёл в 14,2 с; пачки пересчитывает один кассир." },
        "nc.handover": { status: "not_visible", note: "Передачи заведующему в ролике нет." },
        "all.personal": { status: "manual", tc: 16.2, links: ["d6"], note: "VLM: телефон над деньгами 16,2 с." },
      },
    },
    phases: [
      { n: 1, label: "клиент подошёл", st: "ok", t: 2.0, note: "2,0 с" },
      { n: 2, label: "документ", st: "ok", t: 2.4, note: "2,2–2,8 с", step: "ci.id" },
      { n: 3, label: "деньги приняты", st: "ok", t: 2.9, iv: [2.5, 3.2], note: "2,5–3,2 с" },
      { n: 4, label: "пересчёт", st: "dev", t: 4.0, iv: [3.2, 4.6], note: "ожидался 3,2–4,6 с — не было", link: "d1", step: "ci.recount" },
      { n: 5, label: "в ящик", st: "dev", t: 7.5, iv: [4.6, 14.0], note: "деньги остались на столе", link: "d2", step: "ci.lock" },
      { n: 6, label: "кассир на месте", st: "dev", t: 12.0, iv: [11.8, 13.6], note: "уход при клиенте", link: "d3", step: "ci.stay" },
      { n: 7, label: "клиент ушёл", st: "ok", t: 14.2, note: "14,2 с" },
      { n: 8, label: "пересчёт вдвоём", st: "dev", t: 15.0, iv: [14.6, 15.8], note: "пересчёт в одиночку (тип «Иное», вручную)", link: "d5", step: "nc.control" },
    ],
    items: [
      mk({ id: "d1", tid: "cash_accepted_without_count", kind: "violation", source: "rule", omission: true, title: "Деньги приняты без пересчёта при клиенте", short: "Без пересчёта", tc: 4.0, iv: [3.2, 4.6], conf: 0.82, thr: 0.65, rule: "cash_accepted_without_count", status: "pending",
        desc: "Клиент передал деньги в 2,5 с, в 3,2 с купюры легли на стол; полистного пересчёта при клиенте не зафиксировано. Признаки возможного нарушения п. 19 пп. 2 Правил № 231 (по бездействию).",
        visual: "Купюры лежат на столе, пересчёта нет, клиент у окна", cannot: "Сумму и номиналы; был ли пересчёт вне кадра", frames: [f(3.0), f(4.0, "desk"), f(5.0)] }),
      mk({ id: "d3", tid: "cash_unattended", kind: "violation", source: "rule", omission: false, title: "Кассир ушёл, деньги остались на столе", short: "Деньги без присмотра", tc: 12.0, iv: [11.8, 13.6], conf: 0.86, thr: 0.6, rule: "cash_unattended", status: "confirmed", step: "ci.stay",
        desc: "Кассир отходит от стола в 11,8 с при клиенте и возвращается в 13,6 с; купюры всё это время лежат в зоне «стол». Признаки возможного нарушения п. 22 и п. 20 ч. 2 Правил № 231.", visual: "Кресло кассира пустое, купюры на столе, клиент у стола", cannot: "Причину ухода; сумму; чьи это деньги",
        frames: [f(11.0), f(12.0, "chair"), f(13.0)] }),
      mk({ id: "d2", tid: "cash_within_client_reach", kind: "violation", source: "rule", omission: false, title: "Купюры у края стола со стороны клиента", short: "В зоне клиента", tc: 12.4, iv: [11.8, 13.6], conf: 0.71, thr: 0.6, rule: "cash_within_client_reach", status: "pending", step: "ci.lock",
        desc: "Пока кассира нет, купюры лежат у границы зон «стол» и «сторона клиента» — в зоне досягаемости клиента, не в устройстве под ключ. Признаки возможного нарушения п. 20 ч. 2 Правил № 231.",
        visual: "Купюры у края стола, ближе к клиенту; кассира нет", cannot: "Что клиент тянулся к деньгам; сумму", frames: [f(11.0), f(12.0, "desk"), f(13.0)] }),
      mk({ id: "d8", tid: "workstation_unlocked", kind: "observation", source: "rule", omission: false, title: "Экран ноутбука открыт, кассира нет", short: "ПК не заблокирован", tc: 12.8, iv: [11.8, 13.6], conf: 0.62, thr: 0.7, rule: "workstation_unlocked", status: "pending",
        desc: "Ноутбук на столе открыт с включённым экраном, пока кассир отошёл. Уверенность ниже порога (0,70); нормы в актах РК нет — правило ИБ банка. Проверить вручную.",
        visual: "Открытая крышка, светится экран; кассира нет", cannot: "Что экран не заблокирован (экран блокировки выглядит похоже)", frames: [f(11.0), f(12.0, "deskall"), f(13.0)] }),
      mk({ id: "d5", tid: "other", kind: "observation", source: "rule", omission: false, title: "Пересчёт пачек без контролирующего", short: "Пересчёт в одиночку", tc: 14.6, iv: [14.6, 15.8], conf: 0.79, thr: 0.85, rule: "other", status: "pending", step: "nc.control",
        desc: "Клиент ушёл в 14,2 с; пачки пересчитывает один кассир, второго сотрудника нет. Отклонение от шага эталона «Без клиента» (п. 42 Правил № 231), но в rules.json отдельного типа нет — тип «Иное», порог 0,85 не пройден. Проверить вручную.",
        visual: "Один сотрудник, пачки в счётной машинке", cannot: "Что второй сотрудник не стоит вне кадра", frames: [f(14.0), f(14.6, "device"), f(15.5)] }),
      mk({ id: "d6", tid: "phone_or_personal_items", kind: "observation", source: "vlm", omission: false, title: "Телефон над наличными", short: "Телефон", tc: 16.2, iv: [15.8, 16.8], conf: 0.58, thr: 0.6, rule: null, status: "pending",
        desc: "VLM видит смартфон в руке кассира над купюрами. Сигнал второго судьи, ниже порога — проверить вручную.", visual: "Тёмный прямоугольник над купюрами", cannot: "Что телефон с камерой (без камеры — разрешено, п. 12 ч. 2); что велась съёмка",
        frames: [f(15.5), f(16.2, "phone"), f(16.5)] }),
      mk({ id: "d7", tid: "cash_unattended", kind: "observation", source: "rule", omission: false, title: "Хранение в сейфе не проверено", short: "Сейф: вручную", tc: 16.6, iv: [15.6, DUR], conf: 0, thr: null, rule: null, status: "pending", zoneMissing: "safe", step: "ci.lock",
        desc: "Зона «сейф» не распознана, поэтому проверка «ранее принятые деньги убраны в устройство под ключ» (п. 20 ч. 2) не выполнялась. Последнее известное положение — «в машинке». Проверить вручную.",
        visual: "Деньги в зоне «счётная машинка»; область сейфа не определена детектором", cannot: "Были ли деньги убраны в сейф после пересчёта",
        frames: [f(15.5), f(16.5, "device"), f(16.2)], mi: 1, flab: ["до", "последний кадр", "рядом"] }),
    ],
  },
  demo_clean: {
    key: "demo_clean", label: "Демо: чисто", src: "demo", file: "sample.mov", job: "f07a2c3be19d4e5aa1c8d6b29e4f7031", dur: DUR, start: 8.4, sel: null,
    tracks: { ...empty(),
      client_at_window: [{ a: 2.0, b: DUR, label: "клиент" }],
      cashier_at_desk: [{ a: 0, b: DUR, label: "кассир" }],
      cash_location: [
        { a: 9.0, b: 9.5, label: "", state: "hands" }, { a: 9.5, b: 12.0, label: "в машинке", state: "counter" },
        { a: 12.0, b: 13.0, label: "", state: "hands" }, { a: 13.0, b: DUR, label: "в сейфе", state: "safe" }],
      counting: [{ a: 9.5, b: 12.0, label: "пересчёт" }],
      document_card: [{ a: 2.2, b: 2.8, label: "" }],
    },
    gaps: [], items: [], sample: [1.0, 8.4, 16.5], zonesFound: ["safe", "desk", "counter", "client"],
    sessions: [{ type: "cash_in", a: 2.0, b: DUR, conf: 0.9 }],
    results: {
      cash_in: {
        "ci.id": { status: "done", tc: 2.4, note: "Передача документа видна (2,2–2,8 с)." },
        "ci.recount": { status: "done", tc: 9.5, note: "Пересчёт в машинке при клиенте 9,5–12,0 с." },
        "ci.lock": { status: "done", tc: 13.0, note: "Деньги убраны в сейф в 13,0 с." },
        "ci.stay": { status: "done", tc: 2.0, note: "Кассир за столом весь ролик." },
        "all.personal": { status: "done", note: "Личных вещей и телефона не обнаружено." },
      },
    },
    phases: [
      { n: 1, label: "клиент подошёл", st: "ok", t: 2.0, note: "2,0 с" },
      { n: 2, label: "документ", st: "ok", t: 2.4, note: "2,2–2,8 с", step: "ci.id" },
      { n: 3, label: "деньги приняты", st: "ok", t: 9.2, iv: [9.0, 9.5], note: "9,0 с" },
      { n: 4, label: "пересчёт", st: "ok", t: 10.7, iv: [9.5, 12.0], note: "при клиенте", step: "ci.recount" },
      { n: 5, label: "в ящик", st: "ok", t: 13.0, iv: [12.0, 13.0], note: "в сейф", step: "ci.lock" },
      { n: 6, label: "клиент ушёл", st: "nv", note: "после конца ролика" },
    ],
  },
}

export const fmt = (t: number) => {
  t = Math.max(0, t)
  const m = Math.floor(t / 60), s = t - m * 60
  return String(m).padStart(2, "0") + ":" + (s < 10 ? "0" : "") + s.toFixed(1)
}
export function plural(n: number, a: string, b: string, c: string) {
  const m = n % 10, h = n % 100
  return m == 1 && h != 11 ? a : m >= 2 && m <= 4 && (h < 10 || h >= 20) ? b : c
}
export const isViolation = (it: Item) => it.status !== "rejected" && (it.status === "confirmed" || (it.kind === "violation" && typeOf(it.tid).count_in_verdict))
export const needsReview = (it: Item) => !isViolation(it) && it.status === "pending"
export const OPS: Record<Status, string> = { pending: "pending", confirmed: "confirmed_by_operator", rejected: "rejected_by_operator" }

const refObj = (c: RuleCite) => ({ doc: `${RULE_ACTS[c.act]?.short ?? c.act} — ${RULE_ACTS[c.act]?.number ?? ""}`.trim(), clause: c.clause, quote: c.quote, url: c.url })
const B64 = (t: number) => `/9j/4AAQSkZJRg…(${B64KB[t.toFixed(1)]} KB)`

/* статус шага с учётом решений оператора по связанным находкам */
export function stepResult(S: Scenario, sk: SessionKey, id: string): StepResult | null {
  if (!S.sessions.some((s) => s.type === sk)) return null
  if (STEPS[id].obs === "off") return { status: "off", note: "Не видно на видео (подписи, штампы, документы) — в счёт не идёт." }
  return S.results[sk]?.[id] ?? { status: "not_visible", note: "В ролике не наблюдалось." }
}
export function effStatus(r: StepResult, items: Item[]): ProcStatus {
  const ls = (r.links ?? []).map((id) => items.find((x) => x.id === id)).filter(Boolean) as Item[]
  if (!ls.length) return r.status
  if (ls.some(isViolation)) return "missed"
  if (ls.some(needsReview)) return r.status === "done" ? "done" : "manual"
  return r.status === "missed" ? "manual" : r.status
}
export function compliance(S: Scenario, sk: SessionKey, items: Item[]) {
  let total = 0, ok = 0, manual = 0, off = 0
  for (const id of BASELINE[sk]) {
    const r = stepResult(S, sk, id); if (!r) continue
    const s = effStatus(r, items)
    if (s === "off") off++
    if (s === "done" || s === "missed" || s === "manual") total++
    if (s === "done") ok++
    if (s === "manual") manual++
  }
  return { total, ok, manual, off }
}
const PROC_JSON: Record<ProcStatus, string> = { done: "done", missed: "deviation", na: "n_a", manual: "manual_review", not_visible: "not_visible", off: "not_observable_on_video" }

/* Поля, согласованные с бэкендом (остальные extras — предложение, нужен апрув) */
export const AGREED_EXTRAS = ["type_id", "confidence", "window_sec", "rule_ref", "rule{strength, citations}", "observations", "tracks", "unanalyzed_ranges", "needs_manual_review"]
export const PROPOSED_EXTRAS = ["group", "baseline_step", "session_type", "sessions", "compliance", "procedure_steps", "operator_status", "zones", "cash_location"]

export function buildResult(S: Scenario, items: Item[]) {
  const v = items.filter(isViolation).length
  const n = items.filter(needsReview).length + S.gaps.length
  const viol: unknown[] = [], obs: unknown[] = []
  for (const it of items) {
    const t = typeOf(it.tid)
    const o: Record<string, unknown> = {
      type: t.name_ru, type_id: it.tid, timecode_sec: it.tc, description: it.desc,
      evidence_frames: it.frames.map((fr) => ({ timestamp_sec: fr.t, image_base64: B64(fr.t) })),
      confidence: it.conf, window_sec: [it.iv[0], +it.iv[1].toFixed(2)], rule_ref: t.citations.length ? refObj(t.citations[0]) : null,
      rule: { strength: t.strength, has_solid_clause: t.has_solid_clause, count_in_verdict: t.count_in_verdict, threshold: t.threshold, citations: t.citations.map(refObj) },
      group: t.cat, baseline_step: it.step, title: it.title,
    }
    if (!t.citations.length) o.rule_status = "no_norm_in_rules_json"
    if (!t.count_in_verdict) o.reason_not_counted = "count_in_verdict=false в rules.json"
    if (it.zoneMissing) o.rule_status = "zone_not_detected_manual_review"
    o.source = it.source
    o.operator_status = OPS[it.status]
    ;(isViolation(it) || (it.kind === "violation" && it.status === "rejected") ? viol : obs).push(o)
  }
  const tracks: { label: TrackKey; start_sec: number; end_sec: number; state?: CashState }[] = []
  for (const tr of TRACKS) for (const s of S.tracks[tr.key]) tracks.push({ label: tr.key, start_sec: s.a, end_sec: +s.b.toFixed(2), ...(s.state ? { state: s.state } : {}) })
  tracks.sort((x, y) => x.start_sec - y.start_sec)
  const steps: unknown[] = []
  let tot = 0, okc = 0
  for (const ss of S.sessions) {
    const c = compliance(S, ss.type, items); tot += c.total; okc += c.ok
    for (const id of BASELINE[ss.type]) {
      const r = stepResult(S, ss.type, id)!, st = STEPS[id]
      steps.push({ id, session: ss.type, status: PROC_JSON[effStatus(r, items)], clause: st.cites.length ? st.cites.map((k) => CITES[k].clause).join(", ") : null,
        ...(r.tc !== undefined ? { timecode_sec: r.tc } : {}), ...(st.internal ? { clause_status: "not_verified_internal" } : {}) })
    }
  }
  return {
    job_id: S.job, status: "done", verdict: v ? "violation" : "no_violation", violations: viol,
    needs_manual_review: n > 0,
    session_type: S.sessions.length ? SESSIONS.find((x) => x.key === S.sessions[0].type)!.json : "unknown",
    sessions: S.sessions.map((s) => ({ type: s.type, start_sec: s.a, end_sec: +s.b.toFixed(2), confidence: s.conf })),
    compliance: { steps_total: tot, steps_ok: okc, score: tot ? +(okc / tot).toFixed(2) : null },
    procedure_steps: steps,
    observations: obs, tracks,
    unanalyzed_ranges: S.gaps.map((g) => ({ start_sec: g.a, end_sec: g.b, reason: g.why })),
    zones: ZONES.filter((z) => S.zonesFound.includes(z.key)).map((z) => ({ label: z.key, polygon: z.polygon })),
    ...(S.zonesFound.length < ZONES.length ? { zones_not_detected: ZONES.filter((z) => !S.zonesFound.includes(z.key)).map((z) => z.key) } : {}),
    meta: { video: S.file, duration_sec: S.dur, width: VW, height: VH, fps: 30, data_source: S.src === "real" ? "real_clip_demo_confidence" : "demo_illustration" },
  }
}

export const CURL = `curl -X POST -H "X-API-Key: $API_KEY" -F file=@video.mov http://HOST:8000/api/v1/analyze
# -> 202 {"job_id":"...","status":"processing"}
curl -H "X-API-Key: $API_KEY" http://HOST:8000/api/v1/jobs/<job_id>`
