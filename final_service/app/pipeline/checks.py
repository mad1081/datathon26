"""Deterministic consistency checks between a model's violations and its own timeline / object states.

The model often describes the correct action in its timeline ("кассир закрывает крышку ноутбука")
and still reports the opposite violation. These checks drop such self-contradicting claims.
"""
import re

LAPTOP_SECURED = re.compile(
    r"(закры\w*[^.;]{0,25}ноутбук|ноутбук\w*[^.;]{0,30}(закрыт|закрыв|опущ|заблок|выключ)"
    r"|крышк\w*[^.;]{0,15}(закры|опущ)|экран\w*[^.;]{0,10}блокир|заблокир\w*[^.;]{0,20}(экран|ноутбук|компьютер))")
CASHIER_LEAVES = re.compile(r"(кассир\w*[^.;]{0,40}(выход|выш|уход|ушл|ушёл|покида|покинул)|помещени\w* пуст)")
SOMEONE_ENTERS = re.compile(r"(вход|вош(ёл|ел|ла|ли)|заход|появля\w*[^.;]{0,20}(двер|проём|проем))")
CASH_WORDS = re.compile(r"(денег|деньги|деньгам|купюр|пачк|наличн|пересч|банкнот|машинк|счётн|счетн)")
COUNTED = re.compile(r"(пересч|подсчит|считает|счётн\w* машин|счетн\w* машин|в машинк|купюросч)")
NOT_COUNTED = re.compile(r"(без[^.;]{0,20}пересч|не пересч)")
FOOD_WORDS = re.compile(r"(кружк|стакан|чашк|напит|пьёт|пьет|глото|еда|ест |печень|бутылк|кофе|чай)")


def _events(parsed):
    out = []
    for e in parsed.get("timeline") or []:
        if isinstance(e, dict):
            out.append((_t(e.get("t")), str(e.get("event") or "").lower()))
    for s in parsed.get("object_states") or []:
        if isinstance(s, dict):
            out.append((_t(s.get("t")), f"{s.get('object', '')}: {s.get('state', '')}".lower()))
    return sorted(out, key=lambda x: x[0])


def _t(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def contradicted(v, parsed):
    """Return a reason string if violation `v` contradicts the model's own description, else None."""
    if not isinstance(parsed, dict):
        return None
    events = _events(parsed)
    tid, tc = v["type_id"], v["timecode_sec"]

    if tid == "workstation_unlocked":
        if any(LAPTOP_SECURED.search(text) for _, text in events):
            return "в хронологии ноутбук закрыт или заблокирован"

    if tid == "door_left_open":
        exits = [t for t, text in events if CASHIER_LEAVES.search(text)]
        if exits:
            t_exit = exits[0]
            entered_after = any(t > t_exit and SOMEONE_ENTERS.search(text) and not CASHIER_LEAVES.search(text)
                                for t, text in events)
            if tc >= t_exit - 2 and not entered_after:
                return "дверь открыта при выходе кассира, после этого никто не входил"

    if tid == "cash_accepted_without_count":
        if any(t <= tc + 1 and COUNTED.search(text) and not NOT_COUNTED.search(text) for t, text in events):
            return "в хронологии деньги пересчитываются до этого момента"

    if tid == "eating_drinking":
        near = [text for t, text in events if abs(t - tc) <= 10]
        if not any(CASH_WORDS.search(text) for text in near) and not CASH_WORDS.search(v.get("observed", "").lower()):
            return "напиток или еда без наличных рядом"

    return None
