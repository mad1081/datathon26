import csv
import os
import re
from pathlib import Path

import openpyxl

import config

ORGANIZER_XLSX = Path(os.getenv("ORGANIZER_LABELS", config.ROOT_DIR / "open" / "open_labels.xlsx"))
TEAM_CSV = Path(os.getenv("TEAM_LABELS", Path.home() / "Downloads" / "labeled_dataset_pairs.csv"))

DUPLICATES = {"X-47": "X-4", "X-48": "X-5"}

# keyword (lowercase substring of teammate "Тип нарушения") -> acceptable rule ids
TYPE_KEYWORDS = [
    ("сомнительн", ["suspicious_note_returned"]),
    ("инкассатор", ["collector_bag_no_check", "no_client_id_check"]),
    ("без предъявления документа", ["no_client_id_check"]),
    ("смешаны", ["foreign_cash_on_desk"]),
    ("положены рядом", ["foreign_cash_on_desk"]),
    ("деньги клиента 1 не убраны", ["foreign_cash_on_desk", "cash_unattended"]),
    ("ноутбук", ["workstation_unlocked"]),
    ("пересчёт пропущен", ["cash_accepted_without_count"]),
    ("сумка с ценностями", ["cash_unattended"]),
    ("второй посетитель", ["outsider_in_cash_room"]),
    ("посторонн", ["outsider_in_cash_room"]),
    ("сейф не закрыт", ["safe_left_open"]),
    ("ключ в замке", ["safe_key_left"]),
    ("печати", ["seals_docs_unattended"]),
    ("не убраны в сейф", ["cash_unattended"]),
    ("дверь открыта", ["door_left_open"]),
    ("пересчёт после ухода клиента", ["counting_without_client"]),
    ("личные вещи", ["phone_or_personal_items"]),
    ("напиток", ["eating_drinking"]),
]

# Videos whose teammate type text is empty but the violation is described elsewhere.
TYPE_OVERRIDES = {
    "X-44": ["other", "counting_without_controller", "suspicious_note_returned"],
}


def map_type_text(text):
    t = (text or "").lower().replace("ё", "е")
    ids = []
    for kw, rule_ids in TYPE_KEYWORDS:
        if kw.replace("ё", "е") in t:
            for r in rule_ids:
                if r not in ids:
                    ids.append(r)
    return ids


def parse_seconds(text):
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).lower()
    if not s.strip():
        return None
    total = 0.0
    found = False
    m = re.search(r"(\d+)\s*мин", s)
    if m:
        total += 60 * int(m.group(1))
        found = True
    m = re.search(r"(\d+)\s*сек", s)
    if m:
        total += int(m.group(1))
        found = True
    if not found:
        m = re.search(r"\d+", s)
        if m:
            total = float(m.group(0))
            found = True
    return total if found else None


def load_ground_truth():
    """Return {key: {"violation": bool, "seconds": [..], "type_texts": [..], "type_ids": [..], "scenario": str}}."""
    gt = {}
    wb = openpyxl.load_workbook(ORGANIZER_XLSX, read_only=True)
    ws = wb.active
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not row or not row[0]:
            continue
        key = config.video_key(row[0])
        target = DUPLICATES.get(key, key)
        is_v = str(row[2]).strip().lower() == "нарушение"
        entry = gt.setdefault(target, {"violation": False, "seconds": [], "type_texts": [], "type_ids": [],
                                       "scenario": ""})
        if key == target:
            entry["violation"] = is_v
        sec = parse_seconds(row[1])
        if sec is not None and sec not in entry["seconds"]:
            entry["seconds"].append(sec)

    if TEAM_CSV.exists():
        with open(TEAM_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = config.video_key(row.get("наименование файла", ""))
                if key not in gt:
                    continue
                entry = gt[key]
                sec = parse_seconds(row.get("таймстемп"))
                if sec is not None and sec not in entry["seconds"]:
                    entry["seconds"].append(sec)
                txt = (row.get("Тип нарушения") or "").strip()
                if txt:
                    entry["type_texts"].append(txt)
                    for rid in map_type_text(txt):
                        if rid not in entry["type_ids"]:
                            entry["type_ids"].append(rid)
                entry["scenario"] = entry["scenario"] or (row.get("Сценарий") or "").strip()
    for key, ids in TYPE_OVERRIDES.items():
        if key in gt and not gt[key]["type_ids"]:
            gt[key]["type_ids"] = list(ids)
    return gt


def mapping_table(gt):
    lines = []
    for key in sorted(gt, key=config.video_number):
        e = gt[key]
        if not e["violation"]:
            continue
        lines.append(f"{key:6s} {'/'.join(str(int(s)) for s in e['seconds']):8s} "
                     f"{' | '.join(e['type_texts']) or '(empty)'}  ->  {', '.join(e['type_ids']) or '-'}")
    return "\n".join(lines)
