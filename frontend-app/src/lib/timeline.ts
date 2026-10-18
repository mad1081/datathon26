import type { ApiTimelineEvent, ApiViolation } from "./api"

const NEAR_SEC = 2
/** Индексы событий хронологии, ближайших к таймкоду каждого нарушения (не дальше NEAR_SEC). */
export function violationRows(timeline: ApiTimelineEvent[], violations: ApiViolation[]): Set<number> {
  const rows = new Set<number>()
  for (const v of violations) {
    let best = -1
    timeline.forEach((e, i) => {
      if (Math.abs(e.t - v.timecode_sec) <= NEAR_SEC && (best < 0 || Math.abs(e.t - v.timecode_sec) < Math.abs(timeline[best].t - v.timecode_sec))) best = i
    })
    if (best >= 0) rows.add(best)
  }
  return rows
}

/** Индекс события, которое идёт в момент ph (последнее с t ≤ ph), или -1. */
export function currentRow(timeline: ApiTimelineEvent[], ph: number): number {
  let cur = -1
  timeline.forEach((e, i) => { if (e.t <= ph) cur = i })
  return cur
}
