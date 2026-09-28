#!/usr/bin/env python3
"""
Summarise how abbreviated the ORIGINAL column names are in the BIRD dev
databases and the two Spider databases used in the experiments.

Each original column name is tokenised (snake / space / camelCase / digits) and
every alphabetic token is checked against an English word list plus a list of
well-known abbreviations.  A column is then:

  descriptive  — every alphabetic token is an English word (e.g. "School Name",
                 "molecule_id" is NOT here because "id" counts as abbreviation)
  partial      — some tokens are words, some are abbreviations (e.g. "CDSCode",
                 "team_api_id", "AvgScrRead" -> Avg/Scr/Read)
  abbreviated  — no alphabetic token is a word (e.g. "cds", "dob", "A3", "LDH")

`id`-only columns ("id", "ID") are reported separately because they are
ubiquitous and arguably not an abbreviation a reader has to decode.

Usage (from schema_effect/):
    .venv/bin/python analysis/summarize_original_column_names.py > docs/original_column_name_summary.md
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from analysis.audit_semantic_mapping import (  # noqa: E402
    BIRD_DBS, SPIDER_DBS, BIRD_DIR, SPIDER_DIR, load_tables,
)

WORDS = {w.strip().lower() for w in Path("/usr/share/dict/words").read_text().splitlines()}
# Tokens that are in the dictionary but are clearly used as abbreviations here.
FORCE_ABBR = {
    "id", "num", "avg", "min", "max", "pct", "cnt", "dt", "nm", "cd", "lat", "lng", "lon",
    "dob", "gk", "sat", "abr", "ops", "dist", "sch", "cnty", "std", "seq",
    "pos", "ref", "no", "tp", "un", "sm", "pt", "fg", "tg", "ua", "alb", "cre", "glu",
    "ssa", "ssb", "rnp", "dna", "ana", "ldh", "cpk", "hgb", "crp", "igg", "igm", "igA", "iga",
    "acl", "wbc", "rbc", "plt", "pic", "tat", "ht", "wt", "attr", "desc", "amt", "qty",
    "yr", "mo", "hr", "sec", "ms", "fk", "pk", "db", "sql", "tv", "vs", "ln", "pi", "tst",
    "takr", "scr", "gs", "doc", "soc", "aac", "nces", "irc", "frpm", "nslp", "calpads",
    "cds", "rtype", "mpg", "ge", "diff", "org", "org_id", "fifa", "cont", "ea", "lac", "got", "alp", "gpt", "kct", "rvvt",
}
FORCE_WORD = {"of", "in", "to", "and", "or", "the", "a", "an", "per", "by", "is", "up", "on", "at",
              "email", "colour", "color", "website", "zip", "url", "api", "milliseconds", "positioning",
              "eyes", "ages", "abbreviation", "database", "dataset", "goalkeeping"}
_SUFFIXES = ("s", "es", "ed", "ing", "er", "est", "ly", "ies")


def _stem_in_words(t: str) -> bool:
    if t in WORDS:
        return True
    for suf in _SUFFIXES:
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            base = t[: -len(suf)]
            if base in WORDS or (suf == "ies" and base + "y" in WORDS) or (suf in ("ing", "ed", "er") and base + "e" in WORDS):
                return True
    return False


# ---------------------------------------------------------------------------
# S2 word inventory: every full-word token that occurs in an ORIGINAL column
# name of the 11 experiment databases, split into three groups.  Used to build
# the S2 (abbreviated) mapping: a word is replaced by its entry here; tokens
# that are already abbreviations, and `id` / `url` / `zip` / `api`, stay as is.
#
#   S2_GROUP_A  — has a conventional abbreviation (developer / domain usage)
#   S2_GROUP_B  — no conventional abbreviation; truncated to 2-5 letters
#   S2_GROUP_C  — short word; truncated where possible, None = keep as is
# ---------------------------------------------------------------------------

S2_GROUP_A = {
    # generic field words
    "number": "num", "name": "nm", "date": "dt", "time": "tm", "type": "typ", "status": "stat",
    "code": "cd", "description": "descr", "amount": "amt", "count": "cnt", "average": "avg",
    "percent": "pct", "year": "yr", "value": "val", "total": "tot", "text": "txt", "symbol": "sym",
    "size": "sz", "reference": "ref", "source": "src", "category": "cat", "location": "loc",
    "position": "pos", "update": "upd", "original": "orig", "option": "opt", "package": "pkg",
    "label": "lbl", "milliseconds": "ms", "email": "eml", "gender": "gndr", "grade": "grd",
    "city": "cty", "fastest": "fast", "positioning": "pos", "long": "lng", "short": "sht",
    # business / finance
    "customer": "cust", "account": "acct", "transaction": "txn", "department": "dept",
    "product": "prod", "client": "clt", "payment": "pmt", "payments": "pmts", "balance": "bal",
    "frequency": "freq", "duration": "dur", "operation": "op", "order": "ord", "income": "inc",
    "expense": "exp", "budget": "bdgt", "received": "rcvd", "approved": "apprv", "price": "prc",
    "currency": "curr", "consumption": "cons", "segment": "seg", "member": "mbr", "event": "evt",
    # geography / address
    "country": "ctry", "state": "st", "street": "str", "district": "dist", "county": "cnty",
    "latitude": "lat", "longitude": "lng", "altitude": "alt", "station": "stn",
    "continent": "cont", "phone": "ph", "website": "web",
    # people / education / medical
    "first": "fst", "last": "lst", "birthday": "bday", "administrator": "adm", "school": "sch",
    "college": "coll", "major": "maj", "academic": "acad", "enrollment": "enrl",
    "eligible": "elig", "educational": "edu", "certification": "cert", "examination": "exam",
    "diagnosis": "diag", "symptoms": "symp", "admission": "adm",
    # measures
    "weight": "wt", "height": "ht", "width": "wdth", "speed": "spd", "points": "pts",
    "rank": "rnk", "round": "rnd", "season": "ssn", "nationality": "nat", "cylinders": "cyl",
    "horsepower": "hp", "accelerate": "accel", "acceleration": "accel", "model": "mdl",
    "maker": "mkr",
    # motorsport / football / media domain usage
    "constructor": "ctor", "driver": "drv", "circuit": "cir", "result": "res", "results": "res",
    "standings": "stnd", "qualifying": "qual", "overall": "ovr", "potential": "pot",
    "preferred": "pref", "attacking": "atk", "defensive": "def", "defence": "def",
    "accuracy": "acc", "control": "ctrl", "aggression": "aggr", "interceptions": "intc",
    "vision": "vis", "penalties": "pen", "possession": "poss", "league": "lg",
    "attribute": "attr", "publisher": "pub", "alignment": "algn", "colour": "clr",
    "power": "pwr", "molecule": "mol", "atom": "atm", "bond": "bnd", "element": "elem", "channel": "ch",
    "series": "ser", "language": "lang", "episode": "ep", "rating": "rtg", "title": "ttl",
    "production": "prod", "definition": "def",
}

S2_GROUP_B = {
    "player": "plyr", "team": "tm", "match": "mtch", "race": "rc", "class": "cls",
    "chance": "chnc", "creation": "crtn", "charter": "chrt", "funding": "fnd",
    "provision": "prov", "meal": "ml", "passing": "pass", "crossing": "crss",
    "finishing": "fnsh", "heading": "hdg", "dribbling": "drbl", "volleys": "vly",
    "curve": "crv", "sprint": "sprt", "agility": "agil", "reactions": "rctn",
    "jumping": "jmp", "stamina": "stam", "strength": "strn", "shooting": "shtg",
    "marking": "mrk", "standing": "stdg", "sliding": "sld", "tackle": "tkl",
    "diving": "dvg", "handling": "hndl", "kicking": "kckg", "reflexes": "rflx",
    "pressure": "prss", "defender": "dfndr", "corner": "cnr", "issued": "issd",
    "forename": "fname", "surname": "sname", "superhero": "sphro", "hero": "hro",
    "viewers": "vwrs", "weekly": "wkly", "directed": "dir", "written": "wrtn",
    "content": "cntnt", "aspect": "aspt", "ratio": "rto", "remaining": "rmn",
    "spent": "spnt", "magnet": "mgnt", "virtual": "virt", "thrombosis": "thrmb",
    "pattern": "ptrn", "qualify": "qual", "offered": "offd", "served": "srvd", "chain": "chn", "shirt": "shrt", "gas": "gs",
    "hight": "hght",
}

S2_GROUP_C = {
    "home": "hm", "away": "aw", "build": "bld", "play": "ply", "work": "wrk", "rate": "rt",
    "free": "fr", "lap": "lp", "laps": "lps", "goal": "gl", "shot": "sht", "shots": "shts",
    "cross": "crs", "kick": "kck", "ball": "bl", "foot": "ft", "line": "lin", "stage": "stg",
    "grid": "grd", "stop": "stp", "wins": "wns", "link": "lnk", "ages": "ags", "low": "lo",
    "high": "hi", "read": "rd", "math": "mth", "write": "wr", "open": "opn",
    "closed": "clsd", "full": "fl", "make": "mk", "share": "shr", "hair": "hr",
    "skin": "skn", "birth": "brth", "loan": "ln", "bank": "bnk", "card": "crd",
    "cost": "cst", "notes": "nts", "view": "vw", "fall": "fll",
    # cannot be shortened meaningfully — kept as is
    "up": None, "air": None, "eye": None, "sex": None, "pay": None, "mail": None,
}

# tokens the dictionary treats as words but which are already abbreviations in
# these schemas (rule 1: keep as is)
S2_ALREADY_ABBREVIATED = {"pro", "cho", "par", "iwa", "wha", "trans", "alt", "enroll"}
S2_KEEP_WORDS = {"id", "url", "zip", "api", "of", "to", "in", "and", "or", "the", "a", "an", "per", "by", "is"}


def tokens(name: str) -> list[str]:
    parts = re.split(r"[^A-Za-z0-9]+", name)
    out = []
    for p in parts:
        if not p:
            continue
        out += re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", p)
    return out


def is_word(tok: str) -> bool:
    t = tok.lower()
    if ID_IS_WORD and t == "id":
        return True
    if t in FORCE_ABBR:
        return False
    if t in FORCE_WORD:
        return True
    if len(t) <= 2:
        return False
    return _stem_in_words(t)


ID_IS_WORD = False


def classify(name: str) -> tuple[str, list[str]]:
    if name.strip().lower() == "id":
        return ("descriptive", []) if ID_IS_WORD else ("id_only", [])
    alpha = [t for t in tokens(name) if t.isalpha()]
    if not alpha:
        return "abbreviated", tokens(name)
    abbr = [t for t in alpha if not is_word(t)]
    if not abbr:
        return "descriptive", []
    if len(abbr) == len(alpha):
        return "abbreviated", abbr
    return "partial", abbr


def main() -> None:
    bird = load_tables(BIRD_DIR / "dev_tables.json")
    spider = load_tables(SPIDER_DIR / "tables.json")
    cats = ["descriptive", "partial", "abbreviated", "id_only"]
    per_db: dict[str, Counter] = {}
    detail: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    abbr_tokens: Counter = Counter()

    for db in BIRD_DBS + SPIDER_DBS:
        tables = bird.get(db) or spider.get(db)
        c = Counter()
        for tbl, cols in tables.items():
            for col in cols:
                cat, abbr = classify(col)
                c[cat] += 1
                detail[db][cat].append((tbl, col, abbr))
                for a in abbr:
                    abbr_tokens[a.lower()] += 1
        per_db[db] = c

    print("# Original column names: how abbreviated are they?\n")
    print("Generated by `analysis/summarize_original_column_names.py` from `dev_tables.json` and Spider `tables.json`.\n")
    print("Categories (per original column name, tokenised on snake/space/camelCase):\n")
    print("- **descriptive** — every alphabetic token is a dictionary word (e.g. `School Name`, `molecule_id` is *not* here since `id` counts as an abbreviation)")
    print("- **partial** — mixes words and abbreviations (e.g. `CDSCode`, `team_api_id`, `Enrollment (K-12)`)")
    print("- **abbreviated** — no alphabetic token is a word (e.g. `cds`, `dob`, `A3`, `LDH`)")
    print("- **id only** — the column is literally `id` / `ID`\n")
    print("| database | source | columns | descriptive | partial | abbreviated | id only | contains any abbrev. (partial+abbr+id) |")
    print("|--|--|--:|--:|--:|--:|--:|--:|")
    tot = Counter()
    for db in BIRD_DBS + SPIDER_DBS:
        c = per_db[db]; n = sum(c.values()); tot.update(c)
        src = "BIRD" if db in BIRD_DBS else "Spider"
        anyab = c["partial"] + c["abbreviated"] + c["id_only"]
        print(f"| {db} | {src} | {n} | {c['descriptive']} ({c['descriptive']/n:.0%}) | {c['partial']} ({c['partial']/n:.0%}) | "
              f"{c['abbreviated']} ({c['abbreviated']/n:.0%}) | {c['id_only']} | {anyab} ({anyab/n:.0%}) |")
    n = sum(tot.values()); anyab = tot["partial"] + tot["abbreviated"] + tot["id_only"]
    print(f"| **all** | | {n} | {tot['descriptive']} ({tot['descriptive']/n:.0%}) | {tot['partial']} ({tot['partial']/n:.0%}) | "
          f"{tot['abbreviated']} ({tot['abbreviated']/n:.0%}) | {tot['id_only']} | {anyab} ({anyab/n:.0%}) |")

    for src, dbs in (("BIRD", BIRD_DBS), ("Spider", SPIDER_DBS)):
        t = Counter()
        for db in dbs:
            t.update(per_db[db])
        n = sum(t.values()); anyab = t["partial"] + t["abbreviated"] + t["id_only"]
        print(f"\n**{src} total** ({n} columns): descriptive {t['descriptive']} ({t['descriptive']/n:.0%}), "
              f"partial {t['partial']} ({t['partial']/n:.0%}), abbreviated {t['abbreviated']} ({t['abbreviated']/n:.0%}), "
              f"id only {t['id_only']}; contains any abbreviation {anyab} ({anyab/n:.0%}).")

    # ---- second view: treat `id` as an ordinary word (so `molecule_id` is descriptive)
    global ID_IS_WORD
    ID_IS_WORD = True
    print("\n## Same counts with `id` treated as an ordinary word\n")
    print("`_id` suffixes are so conventional that a reader does not need to decode them; this view counts them as words.\n")
    print("| database | source | columns | descriptive | partial | abbreviated |")
    print("|--|--|--:|--:|--:|--:|")
    tot2 = Counter(); per_src = {"BIRD": Counter(), "Spider": Counter()}
    for db in BIRD_DBS + SPIDER_DBS:
        tables = bird.get(db) or spider.get(db)
        c = Counter(classify(col)[0] for cols in tables.values() for col in cols)
        n = sum(c.values()); tot2.update(c)
        src = "BIRD" if db in BIRD_DBS else "Spider"; per_src[src].update(c)
        print(f"| {db} | {src} | {n} | {c['descriptive']} ({c['descriptive']/n:.0%}) | {c['partial']} ({c['partial']/n:.0%}) | {c['abbreviated']} ({c['abbreviated']/n:.0%}) |")
    for src in ("BIRD", "Spider"):
        c = per_src[src]; n = sum(c.values())
        print(f"| **{src} total** | | {n} | {c['descriptive']} ({c['descriptive']/n:.0%}) | {c['partial']} ({c['partial']/n:.0%}) | {c['abbreviated']} ({c['abbreviated']/n:.0%}) |")
    n = sum(tot2.values())
    print(f"| **all** | | {n} | {tot2['descriptive']} ({tot2['descriptive']/n:.0%}) | {tot2['partial']} ({tot2['partial']/n:.0%}) | {tot2['abbreviated']} ({tot2['abbreviated']/n:.0%}) |")
    ID_IS_WORD = False

    print("\n## Most frequent abbreviation tokens\n")
    print("| token | count |\n|--|--:|")
    for tok, k in abbr_tokens.most_common(40):
        print(f"| `{tok}` | {k} |")

    # ---- S2 word inventory --------------------------------------------------
    words: Counter = Counter()
    for db in BIRD_DBS + SPIDER_DBS:
        tables = bird.get(db) or spider.get(db)
        for cols in tables.values():
            for col in cols:
                for t in tokens(col):
                    tl = t.lower()
                    if t.isalpha() and is_word(t) and tl not in S2_KEEP_WORDS and tl not in S2_ALREADY_ABBREVIATED:
                        words[tl] += 1
    print("\n## S2 word inventory (full-word tokens in original names)\n")
    print("Groups used to build the S2 mapping (see S2_GROUP_A/B/C in this script).\n")
    for title, grp in (("A — conventional abbreviation", S2_GROUP_A), ("B — truncated (no conventional abbreviation)", S2_GROUP_B), ("C — short words", S2_GROUP_C)):
        items = [(w, words[w]) for w in grp if words[w]]
        print(f"**{title}** ({len(items)} words, {sum(n for _, n in items)} occurrences)\n")
        print("| word | S2 | occurrences |\n|--|--|--:|")
        for w, n in sorted(items, key=lambda x: -x[1]):
            print(f"| {w} | {grp[w] if grp[w] is not None else '(kept)'} | {n} |")
        print()
    uncovered = [w for w in words if w not in S2_GROUP_A and w not in S2_GROUP_B and w not in S2_GROUP_C]
    print("Words not covered by any group: " + (", ".join(sorted(uncovered)) if uncovered else "none") + "\n")

    print("\n## Per-database listing (non-descriptive columns)\n")
    for db in BIRD_DBS + SPIDER_DBS:
        print(f"### {db}\n")
        for cat in ("abbreviated", "partial", "id_only"):
            rows = detail[db][cat]
            if not rows:
                continue
            print(f"**{cat}** ({len(rows)})\n")
            for tbl, col, abbr in rows:
                extra = f"  — abbrev tokens: {', '.join(abbr)}" if abbr and cat == "partial" else ""
                print(f"- `{tbl}.{col}`{extra}")
            print()
        rows = detail[db]["descriptive"]
        print(f"**descriptive** ({len(rows)}): " + ", ".join(f"`{t}.{c}`" for t, c, _ in rows) + "\n")


if __name__ == "__main__":
    main()
