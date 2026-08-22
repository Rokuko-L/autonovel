#!/usr/bin/env python3
"""Generate webui fixtures from a REAL project directory.

Usage: uv run python scratch/gen_webui_fixtures.py [project_dir_name]

Reads world/characters/canon/outline files and emits JSON shaped exactly
like contract.js types into webui/frontend/src/fixtures/. The mock client
then serves real novel data with zero screen changes.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "webui" / "frontend" / "src" / "fixtures"

DEFAULT_PROJECT = "sir the confortable v3"


def clean(t: str) -> str:
    t = t.replace("**", "").replace("*", "").strip()
    return re.sub(r"\s+", " ", t)


def split_h3(md: str):
    """Split '### **Title**' headings -> [(title, body)]."""
    pat = re.compile(r"^###\s+\*\*(.+?)\*\*\s*$", re.M)
    ms = list(pat.finditer(md))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(md)
        out.append((clean(m.group(1)), md[m.end():end]))
    return out


HONORIFICS = {"king", "queen", "prince", "princess", "lady", "lord",
              "sir", "archmage", "the", "master", "dame", "captain"}


def key_name(full: str) -> str:
    """First real given name, skipping honorific prefixes."""
    s = full.split(",")[0].split("(")[0].replace('"', "")
    words = [w for w in s.split() if w]
    if words and words[0].lower() in HONORIFICS and len(words) > 1:
        words = words[1:]
    # stop at prepositions: 'Eris of the Spire' -> 'Eris'
    out = []
    for w in words:
        if w.lower() in {"of", "the"} and out:
            break
        out.append(w)
    return out[0] if out else full


def short_name(full: str) -> str:
    """Compact display name: strip honorifics tail after comma/paren."""
    return key_name(full)


def gen_foundation(p: Path, state: dict) -> dict:
    docs = {}
    for n in ("world", "characters", "canon"):
        f = p / f"{n}.md"
        docs[n] = f.read_text(encoding="utf-8") if f.exists() else ""

    # -- character nodes ------------------------------------------------
    nodes, char_blocks = [], []
    for title, body in split_h3(docs["characters"]):
        m = re.match(r"(\d+)\.\s+(.+)", title)
        if not m:
            continue
        full_name = m.group(2)
        kn = key_name(full_name)
        # aliases: quoted nicknames ('Liliana “Lily” ...' -> also matches 'Lily')
        # handles both straight and typographic quotes
        aliases = {kn, *re.findall(r"[\"“]([^\"”]+)[\"”]", full_name)}
        low = body.lower()
        status = None
        if re.search(r"\bdead\b|deceased|\bkilled\b", low):
            status = "dead?"
        elif re.search(r"\bmissing\b|\bunknown\b|presumed", low):
            status = "unknown"
        char_blocks.append((kn, aliases, body))
        nodes.append({
            "id": f"c{m.group(1)}", "label": kn,
            "kind": "character", "status": status,
        })

    # edges: co-mention between character blocks (real relationships!)
    edges, seen = [], set()
    for a_name, _, a_body in char_blocks:
        for b_name, b_aliases, _ in char_blocks:
            if a_name == b_name:
                continue
            mentioned = any(
                re.search(rf"\b{re.escape(al)}\b", a_body)
                for al in b_aliases if len(al) >= 3)
            if mentioned:
                pair = tuple(sorted((a_name, b_name)))
                if pair not in seen:
                    seen.add(pair)
                    edges.append({
                        "from": next(n["id"] for n in nodes if n["label"] == a_name),
                        "to": next(n["id"] for n in nodes if n["label"] == b_name),
                        "label": "entangled",
                    })

    # -- factions & locations from world.md ------------------------------
    def bullets_under(marker: str, kind: str, limit=5):
        """Faction/location nodes from world.md bullet lists; returns {label: desc}."""
        out = {}
        sec = re.search(
            rf"##\s+\*\*[^*]*{marker}[^*]*\*\*(.*?)(?=\n##\s|\Z)",
            docs["world"], re.I | re.S)
        if not sec:
            return out
        for b, desc in re.findall(r"^-\s+\*\*(.+?)\*\*:?\s*(.*)$",
                                  sec.group(1), re.M):
            label = clean(b).rstrip(":").strip()
            # skip bullets that duplicate a character entry ("The Cult of the
            # Eternal Flame" when 'Cult' is already a registry node)
            if any(w in cn.lower() or cn in label.lower()
                   for w in label.lower().split() if len(w) > 3
                   for cn, _, _ in char_blocks):
                continue
            if sum(1 for n in nodes if n["label"] == label) or \
               sum(1 for n in nodes if n["kind"] == kind) >= limit:
                continue
            nodes.append({"id": f"{kind}{len(nodes)}", "label": label,
                          "kind": kind, "status": None})
            out[label] = clean(desc)
        return out

    faction_descs = bullets_under("POWER GROUPS", "faction")
    location_descs = bullets_under("LOCATION", "location")

    bullets_under("POWER GROUPS", "faction")
    bullets_under("LOCATION", "location")

    # faction/location <-> character edges: character named in the entity's
    # world.md description, or entity named in a character block (real data)
    by_label = {n["label"]: n["id"] for n in nodes}
    for label, desc in {**faction_descs, **location_descs}.items():
        nid = by_label[label]
        for cn, aliases, _ in char_blocks:
            if any(len(a) >= 3 and re.search(rf"\b{re.escape(a)}\b", desc, re.I)
                   for a in aliases):
                edges.append({"from": nid, "to": by_label[cn], "label": "entangled"})
    for n in [x for x in nodes if x["kind"] in ("faction", "location")]:
        core = n["label"].replace("The ", "").split(":")[0].strip()
        if len(core) < 4:
            continue
        for cn, _, cb in char_blocks:
            if re.search(rf"\b{re.escape(core)}\b", cb, re.I):
                pair = tuple(sorted((n["id"], by_label[cn])))
                if pair in seen:
                    continue
                seen.add(pair)
                edges.append({"from": n["id"], "to": by_label[cn],
                              "label": "entangled"})

    return {
        "meta": {
            "title": state.get("title", "Untitled"),
            "score": state.get("foundation_score"),
            "lore": state.get("lore_score"),
            "chaptersTotal": state.get("chapters_total"),
            "phase": state.get("phase"),
        },
        "docs": docs,
        "entities": {"nodes": nodes, "edges": edges},
    }


def gen_ledger(p: Path, state: dict) -> dict:
    total = state.get("chapters_total", 24)

    premise = []
    part1 = p / ".outline_part1.md"
    if part1.exists():
        txt = part1.read_text(encoding="utf-8")
        sec = re.search(r"\*\*PREMISE BEATS:\*\*(.*?)(?=\n\*\*|\n#)", txt, re.S)
        if sec:
            for label in re.findall(r"^- \*\*\d+\.\s*(.+?):", sec.group(1), re.M):
                premise.append({"label": clean(label), "done": True})

    roadmap = []
    rm = p / ".outline_roadmap.md"
    if rm.exists():
        txt = rm.read_text(encoding="utf-8")
        for m in re.finditer(
                r"^###\s+Chapter\s+(\d+):\s*([^\n]*)\n\n(.+?)(?=\n###|\Z)",
                txt, re.M | re.S):
            num, slug, body = int(m.group(1)), m.group(2).strip(), m.group(3).strip()
            sentences = re.split(r"(?<=[.!?])\s+", body)
            roadmap.append({
                "chapter": num,
                "title": slug.replace("_", " ") or f"chapter {num}",
                "beats": [s.strip() for s in sentences[:3] if s.strip()],
            })
        roadmap.sort(key=lambda c: c["chapter"])
    roadmap = roadmap[:6]

    threads = []
    outline = p / "outline.md"
    if outline.exists():
        txt = outline.read_text(encoding="utf-8")
        sec = re.search(r"FORESHADOWING LEDGER\n(.*?)(?=\n\s*\n(?!\s*\|)|\Z)", txt, re.S)
        if sec:
            for row in re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|$",
                                  sec.group(1), re.M):
                thread, planted, harvested = row
                pm = re.search(r"[Cc]h\.?\s*(\d+)", planted)
                hm = re.search(r"[Cc]h\.?\s*(\d+)", harvested)
                if not pm:
                    continue
                threads.append({
                    "thread": clean(thread)[:60],
                    "planted": int(pm.group(1)),
                    "harvest": int(hm.group(1)) if hm else total,
                    "status": "paid off" if hm else "open",
                })
    threads.sort(key=lambda t: t["planted"])

    return {"premiseBeats": premise, "roadmap": roadmap, "threads": threads}


def gen_projects(state: dict, p: Path) -> list:
    items = []
    for d in sorted((ROOT / "projects").iterdir()):
        sf = d / "state.json"
        if not d.is_dir() or not sf.exists():
            continue
        try:
            s = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        manuscript = d / "manuscript.md"
        words = len(manuscript.read_text(encoding="utf-8").split()) if manuscript.exists() else 0
        phase = s.get("phase", "idle") or "idle"
        if phase.startswith("complete"):
            phase = "export"
        items.append({
            "name": d.name,
            "title": s.get("title", "Untitled"),
            "phase": "idle" if s.get("current_focus") == "done" else phase,
            "foundationScore": s.get("foundation_score", 0) or 0,
            "chaptersTotal": s.get("chapters_total", 0) or 0,
            "chaptersDone": s.get("chapters_drafted", 0) or 0,
            "words": words,
            "updatedAt": None,
            "running": False,
            "_primary": d.name == p.name,
        })
    return items


def main():
    proj_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECT
    p = ROOT / "projects" / proj_name
    state = json.loads((p / "state.json").read_text(encoding="utf-8"))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "foundation.json").write_text(
        json.dumps(gen_foundation(p, state), ensure_ascii=False), encoding="utf-8")
    (OUT / "ledger.json").write_text(
        json.dumps(gen_ledger(p, state), ensure_ascii=False), encoding="utf-8")
    (OUT / "projects.json").write_text(
        json.dumps(gen_projects(state, p), ensure_ascii=False), encoding="utf-8")

    print(f"fixtures regenerated from '{proj_name}'")


if __name__ == "__main__":
    main()
