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

/* ---- таксономия нарушений ---- */
export type CatKey = "presence" | "cash" | "recount" | "personal" | "access"
export const CATEGORIES: Record<CatKey, { label: string; color: string }> = {
  presence: { label: "Присутствие", color: "#7C3AED" },
  cash: { label: "Наличные", color: "#D97706" },
  recount: { label: "Пересчёт", color: "#C2185B" },
  personal: { label: "Личные вещи", color: "#0E8FA8" },
  access: { label: "Доступ", color: "#475569" },
}
export type VCode = "V-ABSENT" | "V-CASH-OPEN" | "V-NO-RECOUNT" | "V-CASH-OUT-ZONE" | "V-SOLO-COUNT" | "V-PHONE" | "V-VAULT-ACCESS"
export type VType = { code: VCode; title: string; cat: CatKey; severity: "critical" | "medium"; steps: string[]; cites: string[]; detector: string; caveat?: string; derived?: boolean }
export const TAXONOMY: VType[] = [
  { code: "V-ABSENT", title: "Кассир покинул место при клиенте", cat: "presence", severity: "critical", steps: ["ci.stay", "co.stay"], cites: ["R231_22"],
    detector: "кассира нет за столом, пока клиент у окна" },
  { code: "V-CASH-OPEN", title: "Деньги вне запираемого устройства / на столе без кассира", cat: "cash", severity: "critical", steps: ["ci.lock", "se.lock"], cites: ["R231_20_2"],
    detector: "дорожка «Где деньги» = на столе, а кассира нет; или чужие/ранее принятые деньги на столе" },
  { code: "V-NO-RECOUNT", title: "Нет пересчёта при клиенте", cat: "recount", severity: "critical", steps: ["ci.recount", "co.recount"], cites: ["R231_19_2", "R231_20_1", "R231_31_4"],
    detector: "деньги приняты/выданы, а пересчёта при клиенте не было (по бездействию) или пересчёт без клиента",
    caveat: "Целые корешки с неповреждённой упаковкой выдаются по надписи без полистного пересчёта (п. 32) — при выдаче проверить упаковку." },
  { code: "V-CASH-OUT-ZONE", title: "Деньги унесены из зоны окна", cat: "cash", severity: "medium", steps: ["ci.lock"], cites: [], derived: true,
    detector: "купюры пересекают границу зон «стол/окно» не в сторону сейфа",
    caveat: "Производный признак детектора: прямого пункта «деньги не покидают зону окна» в Правилах нет. Связь с п. 20 — по смыслу, не цитата. Без подтверждения оператора в вердикт не идёт." },
  { code: "V-SOLO-COUNT", title: "Пересчёт пачек без контролирующего работника", cat: "recount", severity: "medium", steps: ["nc.control"], cites: ["R231_42"],
    detector: "пересчёт, клиента нет, у стола один сотрудник",
    caveat: "Исключение п. 42: операции приёма и выдачи клиенту — если клиент у окна, правило не применяется." },
  { code: "V-PHONE", title: "Личные вещи / смартфон в кассовом узле", cat: "personal", severity: "medium", steps: ["all.personal"], cites: ["R231_12", "R231_12_2"],
    detector: "телефон в руках или на столе кассира",
    caveat: "Средства связи без фото/видео разрешены (п. 12 ч. 2) — по видео не отличить, всегда ручная проверка." },
  { code: "V-VAULT-ACCESS", title: "Кладовая: один человек / вход без сопровождения", cat: "access", severity: "critical", steps: ["va.access"], cites: ["R231_75", "R231_2_16"],
    detector: "в кладовой меньше двух человек или вход без сопровождающего",
    caveat: "Личность не определяется (распознавание лиц запрещено) — только число людей. «Вдвоём в кладовой» прямо в п. 75 не записано; п. 2 пп. 16 — о числе назначенных ответственных (не менее двух). Толкование — согласовать." },
]
export const TYPE_BY_CODE = Object.fromEntries(TAXONOMY.map((t) => [t.code, t])) as Record<VCode, VType>
export const SEVERITY = { critical: { label: "критичное", cls: "bg-destructive text-white" }, medium: { label: "среднее", cls: "bg-warning-bg text-warning ring-1 ring-warning-border" } }
