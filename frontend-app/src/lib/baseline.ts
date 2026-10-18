/* Эталон кассовой процедуры (по воркфлоу Анны, Правила НБРК №231) + таксономия нарушений.
   Пункты — только из norms.ts (дословно, якоря сверены). Где пункта в Правилах нет — internal / derived,
   в UI показывается бейдж «не сверено». */

export type SessionKey = "cash_in" | "cash_out" | "no_client" | "collection" | "vault" | "start_end"
export const SESSIONS: { key: SessionKey; label: string; json: string; hint: string }[] = [
  { key: "cash_in", label: "Приём", json: "cash_in", hint: "клиент вносит наличные (п. 19–22)" },
  { key: "cash_out", label: "Выдача", json: "cash_out", hint: "клиент снимает наличные (п. 31–32)" },
  { key: "no_client", label: "Без клиента", json: "no_client", hint: "пересчёт, сортировка, упаковка, сдача заведующему (п. 23, 42–43)" },
  { key: "collection", label: "Инкассация", json: "collection", hint: "приём от инкассаторов (п. 24–25; Правила №14 п. 21)" },
  { key: "vault", label: "Кладовая", json: "vault", hint: "кладовая / сейфовая комната (п. 74–78)" },
  { key: "start_end", label: "Начало/конец дня", json: "start_end", hint: "открытие и закрытие кассы" },
]
export const SESSION_BY_KEY = Object.fromEntries(SESSIONS.map((s) => [s.key, s])) as Record<SessionKey, (typeof SESSIONS)[number]>

/* obs: "video" — шаг виден на камере (хотя бы частично); "off" — вне видео (подписи, штампы, типы документов), в счёт не идёт */
export type BaseStep = { id: string; title: string; cites: string[]; obs: "video" | "off"; internal?: string; how?: string }
export const STEPS: Record<string, BaseStep> = {
  "all.personal": { id: "all.personal", title: "Личные вещи и смартфон — вне кассового узла", cites: ["R231_12", "R231_12_2"], obs: "video", how: "детектор телефона в руках/на столе; телефон без камеры разрешён — по видео не отличить" },
  "se.reinf": { id: "se.reinf", title: "Подкрепление от заведующего — в ящик / сейф на рабочем месте", cites: [], obs: "video", internal: "внутренние документы банка — пункт Правил не указан" },
  "se.lock": { id: "se.lock", title: "Ящик / сейф закрыт на ключ, открытыми деньги не лежат", cites: ["R231_20_2"], obs: "video" },
  "se.vault": { id: "se.vault", title: "Конец дня: все деньги — в кладовую", cites: ["R231_74"], obs: "video", how: "видно, что стол опустел; учёт в АЦС — вне видео" },
  "se.empty": { id: "se.empty", title: "На столах ничего не остаётся", cites: [], obs: "video", internal: "из воркфлоу; прямого пункта в Правилах не найдено" },

  "ci.id": { id: "ci.id", title: "Сверка клиента с удостоверением / цифровым документом", cites: ["R231_19_1"], obs: "video", how: "видна передача документа; тип документа и лицо не распознаются" },
  "ci.recount": { id: "ci.recount", title: "Полистный пересчёт при клиенте + проверка подлинности", cites: ["R231_19_2", "R231_20_1"], obs: "video" },
  "ci.separate": { id: "ci.separate", title: "По каждому приходному документу — отдельно", cites: ["R231_21"], obs: "off" },
  "ci.sign": { id: "ci.sign", title: "Сверка суммы с документом, подписи, штамп", cites: ["R231_19_3_5"], obs: "off" },
  "ci.receipt": { id: "ci.receipt", title: "Подтверждающий документ клиенту", cites: ["R231_19_6"], obs: "off" },
  "ci.lock": { id: "ci.lock", title: "Сразу в запираемое устройство; на столе — только деньги текущего клиента", cites: ["R231_20_2"], obs: "video" },
  "ci.stay": { id: "ci.stay", title: "Кассир не уходит до конца обслуживания", cites: ["R231_22"], obs: "video" },

  "co.id": { id: "co.id", title: "Сверка клиента с документом", cites: ["R231_31_1"], obs: "video", how: "видна передача документа; тип и лицо не распознаются" },
  "co.sign": { id: "co.sign", title: "Проверка подписей клиента", cites: ["R231_31_2"], obs: "off" },
  "co.prepare": { id: "co.prepare", title: "Достать нужную сумму из ящика", cites: ["R231_31_3"], obs: "video" },
  "co.recount": { id: "co.recount", title: "Пересчитать при клиенте и выдать (целые корешки — по надписи)", cites: ["R231_31_4", "R231_32"], obs: "video" },
  "co.docs": { id: "co.docs", title: "Подпись, штамп, подтверждающий документ", cites: ["R231_31_5_6"], obs: "off" },
  "co.stay": { id: "co.stay", title: "Кассир не уходит до конца обслуживания", cites: ["R231_22"], obs: "video" },

  "nc.control": { id: "nc.control", title: "Пересчёт / сортировка / упаковка — только при контролирующем работнике", cites: ["R231_42"], obs: "video", how: "число сотрудников у стола; исключение п. 42 — операции с клиентом" },
  "nc.sort": { id: "nc.sort", title: "Сортировка по номиналам и годности", cites: ["R231_43"], obs: "off" },
  "nc.handover": { id: "nc.handover", title: "Сдача денег заведующему кассой по приходным документам", cites: ["R231_23"], obs: "video", how: "видна передача; документы — нет" },

  "cl.box": { id: "cl.box", title: "Передача — в закрытом боксе / на погрузочной площадке", cites: ["R14_21"], obs: "video", how: "в тексте п. 21 — требование оборудовать бокс; «чтобы клиенты не видели» — толкование, не цитата" },
  "cl.doc": { id: "cl.doc", title: "Проверка препроводительного документа", cites: ["R231_24_1"], obs: "off" },
  "cl.reg": { id: "cl.reg", title: "Регистрация суммы", cites: ["R231_24_2"], obs: "off" },
  "cl.bag": { id: "cl.bag", title: "Целостность сумки и пломба", cites: ["R231_24_3_4"], obs: "video", how: "сумка видна; пломба на камере мелкая" },
  "cl.open": { id: "cl.open", title: "Сумка повреждена → вскрыть и пересчитать при инкассаторе, акт", cites: ["R231_25"], obs: "video" },

  "va.access": { id: "va.access", title: "Входят только ответственные или в их сопровождении", cites: ["R231_75"], obs: "video", how: "только число людей и сопровождение — личность не определяется (лица не распознаются)" },
  "va.two": { id: "va.two", title: "Ответственных лиц — не менее двух", cites: ["R231_2_16"], obs: "off", how: "назначение — по распорядительному документу, не по видео" },
  "va.keys": { id: "va.keys", title: "Ключи и коды — у ответственных", cites: ["R231_76"], obs: "off" },
  "va.store": { id: "va.store", title: "Хранение раздельно по валюте и номиналу", cites: ["R231_77"], obs: "off" },
  "va.check": { id: "va.check", title: "Сверка наличности перед закрытием", cites: ["R231_78"], obs: "off" },
}
export const BASELINE: Record<SessionKey, string[]> = {
  cash_in: ["ci.id", "ci.recount", "ci.separate", "ci.sign", "ci.receipt", "ci.lock", "ci.stay", "all.personal"],
  cash_out: ["co.id", "co.sign", "co.prepare", "co.recount", "co.docs", "co.stay", "all.personal"],
  no_client: ["nc.control", "nc.sort", "nc.handover", "all.personal"],
  collection: ["cl.box", "cl.doc", "cl.reg", "cl.bag", "cl.open"],
  vault: ["va.access", "va.two", "va.keys", "va.store", "va.check"],
  start_end: ["all.personal", "se.reinf", "se.lock", "se.vault", "se.empty"],
}

/* ---- таксономия нарушений = research/rules.json ----
   Группы — только для фильтра в UI (в rules.json категорий нет). Сила основания и «в вердикт» — из rules.json.
   steps — привязка к шагу эталона; пусто → «вне эталона». */
import { RULES, RULE_BY_ID, type Rule } from "./rules"
export type CatKey = "cash" | "check" | "storage" | "workplace" | "access" | "other"
export const CATEGORIES: Record<CatKey, { label: string; color: string }> = {
  cash: { label: "Наличные", color: "#D97706" },
  check: { label: "Пересчёт и проверка", color: "#C2185B" },
  storage: { label: "Хранение", color: "#475569" },
  workplace: { label: "Рабочее место", color: "#0E8FA8" },
  access: { label: "Доступ", color: "#7C3AED" },
  other: { label: "Прочее", color: "#8D93A0" },
}
export const TYPE_META: Record<string, { cat: CatKey; steps: string[] }> = {
  cash_unattended: { cat: "cash", steps: ["ci.stay", "ci.lock", "co.stay"] },
  seals_docs_unattended: { cat: "storage", steps: [] },
  safe_left_open: { cat: "storage", steps: ["se.lock", "ci.lock"] },
  door_left_open: { cat: "access", steps: [] },
  outsider_in_cash_room: { cat: "access", steps: ["va.access"] },
  cash_out_of_view: { cat: "cash", steps: [] },
  collector_bag_no_check: { cat: "check", steps: ["cl.bag", "cl.doc"] },
  cash_within_client_reach: { cat: "cash", steps: ["ci.lock"] },
  counting_without_client: { cat: "check", steps: ["ci.recount"] },
  issue_without_count: { cat: "check", steps: ["co.recount"] },
  phone_or_personal_items: { cat: "workplace", steps: ["all.personal"] },
  safe_opened_with_client: { cat: "storage", steps: [] },
  eating_drinking: { cat: "workplace", steps: ["all.personal"] },
  no_client_id_check: { cat: "check", steps: ["ci.id"] },
  foreign_cash_on_desk: { cat: "cash", steps: ["ci.lock"] },
  cash_accepted_without_count: { cat: "check", steps: ["ci.recount"] },
  suspicious_note_returned: { cat: "check", steps: [] },
  safe_key_left: { cat: "storage", steps: ["se.lock"] },
  workstation_unlocked: { cat: "workplace", steps: [] },
  counting_without_controller: { cat: "check", steps: ["nc.control"] },
  other: { cat: "other", steps: [] },
}
export const typeOf = (id: string): Rule & { cat: CatKey; steps: string[] } => ({ ...RULE_BY_ID[id], ...(TYPE_META[id] ?? { cat: "other", steps: [] }) })
export { RULES, RULE_BY_ID }
export const OUTSIDE_VERDICT = "вне вердикта, на ручную проверку"
export const STRENGTH: Record<Rule["strength"], { label: string; cls: string }> = {
  strong: { label: "сильное основание", cls: "bg-success-bg text-success ring-1 ring-success/30" },
  medium: { label: "среднее основание", cls: "bg-muted text-foreground/80 ring-1 ring-border" },
  weak: { label: "косвенное основание", cls: "bg-warning-bg text-warning ring-1 ring-warning-border" },
  none: { label: "нет нормы", cls: "bg-danger-bg text-destructive ring-1 ring-destructive/30" },
  unknown: { label: "норма не определена", cls: "bg-muted text-muted-foreground ring-1 ring-border" },
}
