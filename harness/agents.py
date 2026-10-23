import datetime, json, math, os, re
import ollama
from tools import web_search, news_search, fetch_page

MODEL = os.getenv("AGENT_MODEL", "agent-coder")
CTX = int(os.getenv("AGENT_CTX", "16384"))
YEAR = datetime.datetime.now().year
UNKNOWN = "unknown"
FIELDS = ("what_it_does", "total_funding", "valuation", "status", "latest_news")
TRACE = []


def log(agent, action, detail=""):
    TRACE.append({"agent": agent, "action": action, "detail": str(detail)[:300]})
    print(f"[{agent}] {action} {str(detail)[:100]}")


def llm_json(system, user, retries=3):
    for _ in range(retries):
        r = ollama.chat(
            model=MODEL, format="json", think=False,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            options={"temperature": 0.2, "num_ctx": CTX})
        txt = r["message"]["content"]
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
    return {}


# ---------------------------------------------------------------- helpers
_UNITS = {"trillion": 1e12, "tn": 1e12, "t": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9,
          "million": 1e6, "mn": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}
_MONEY = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(trillion|billion|million|thousand|tn|bn|mn|[tbmk])?\b")
_PUBLIC_HINT = re.compile(r"market cap|nyse|nasdaq|publicly traded|went public|listed on|"
                          r"shares (rose|fell|dropped)|stock (price|dropped|fell|rose)", re.I)


def parse_money(value):
    """'$11.2B (down 55%)' -> 11.2e9 ; unknown/garbage -> 0.0"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    m = _MONEY.search(str(value).lower())
    if not m:
        return 0.0
    num = float(m.group(1).replace(",", ""))
    return num * _UNITS.get(m.group(2) or "", 1)


def is_unknown(v):
    return v is None or str(v).strip().lower() in ("", "unknown", "n/a", "na", "none", "-", "\u2014", "null")


def looks_public(c):
    if str(c.get("status", "")).lower() in ("public", "acquired"):
        return True
    blob = " ".join(str(c.get(k, "")) for k in ("what_it_does", "total_funding", "valuation", "latest_news"))
    return bool(_PUBLIC_HINT.search(blob))


def _key(name):
    k = re.sub(r"[^a-z0-9 ]", "", str(name).lower()).strip()
    return re.sub(r"\b(inc|ltd|llc|corp|holdings|technologies|group)$", "", k).strip()


def normalize(s):
    st = str(s.get("status") or "").lower()
    status = ("public" if ("public" in st or "listed" in st) else
              "acquired" if "acquir" in st else
              "private" if ("private" in st or "unicorn" in st) else UNKNOWN)
    out = {"name": str(s.get("name") or "").strip(),
           "what_it_does": str(s.get("what_it_does") or UNKNOWN),
           "total_funding": str(s.get("total_funding") or s.get("funding") or UNKNOWN),
           "valuation": str(s.get("valuation") or UNKNOWN),
           "status": status,
           "latest_news": str(s.get("latest_news") or UNKNOWN)}
    if (not is_unknown(out["total_funding"])
            and out["total_funding"].strip().lower() == out["valuation"].strip().lower()):
        out["total_funding"] = UNKNOWN
    return out


def merge_candidates(cands):
    merged = {}
    for c in cands:
        k = _key(c.get("name", ""))
        if not k:
            continue
        if k not in merged:
            merged[k] = {**c, "mentions": c.get("mentions", 1), "sources": list(c.get("sources", []))}
            continue
        m = merged[k]
        m["mentions"] += c.get("mentions", 1)
        m["sources"] = list(dict.fromkeys(m["sources"] + list(c.get("sources", []))))
        for f in FIELDS:
            if is_unknown(m.get(f)) and not is_unknown(c.get(f)):
                m[f] = c[f]
    return list(merged.values())


def _mag(v):
    return 0.0 if v <= 1 else min(math.log10(v) / 12, 1.0)


def composite(valuation, funding, llm, mentions):
    """0-100: valuation 40%, funding 20%, LLM growth/recency judgement 25%, source mentions 15%."""
    return 100 * (0.40 * _mag(valuation) + 0.20 * _mag(funding)
                  + 0.25 * (llm / 10) + 0.15 * min(mentions, 5) / 5)


# ---------------------------------------------------------------- 1. PLANNER
def planner(category, round_no=1):
    out = llm_json(
        "You plan web searches. Reply as JSON: {\"queries\": [5 short search queries]}.",
        f"Find the top 10 best-performing PRIVATE, venture-backed startups (not publicly listed "
        f"companies) in the category '{category}'. Year is {YEAR}. This is research round "
        f"{round_no}; vary the angle (funding rounds, unicorns, valuation, growth, latest news).")
    queries = out.get("queries") or []
    if not queries:
        queries = [f"top private {category} startups {YEAR}",
                   f"{category} startups biggest funding rounds {YEAR}",
                   f"{category} private unicorn startups valuation {YEAR}",
                   f"fastest growing {category} startups {YEAR}"]
    log("planner", "queries", queries)
    return queries[:6]


# ---------------------------------------------------------------- 2. RESEARCHER
def researcher(queries, fetch_top=6):
    seen, docs = set(), []
    for q in queries:
        for r in web_search(q) + news_search(q, 5):
            if r["url"] and r["url"] not in seen:
                seen.add(r["url"])
                docs.append(r)
    log("researcher", "collected_results", len(docs))
    for d in docs[:fetch_top]:
        d["text"] = fetch_page(d["url"])
    return docs


# ---------------------------------------------------------------- 3. EXTRACTOR
def extractor(category, docs):
    found = []
    for d in docs:
        body = f"{d['title']}\n{d['snippet']}\n{d.get('text', '')}"[:3500]
        out = llm_json(
            "You extract startups from text. Reply as JSON: {\"startups\": [{\"name\", "
            "\"what_it_does\", \"total_funding\", \"valuation\", \"status\", \"latest_news\"}]}. "
            "Rules: total_funding = total capital RAISED; valuation = latest company valuation; "
            "they are different numbers, never copy one into the other; if only one is stated, "
            "leave the other as \"unknown\". status is \"private\", \"public\" (listed on a stock "
            "exchange) or \"acquired\". Only include companies explicitly mentioned. Use "
            "\"unknown\" for anything not stated. Never invent facts.",
            f"Category: {category}\nText:\n{body}")
        for s in out.get("startups", []):
            if not isinstance(s, dict):
                continue
            n = normalize(s)
            if n["name"]:
                found.append({**n, "mentions": 1, "sources": [d["url"]]})
    merged = merge_candidates(found)
    log("extractor", "unique_candidates", len(merged))
    return merged


# ---------------------------------------------------------------- 3b. FILTER
def filter_startups(cands):
    kept = [c for c in cands if not looks_public(c)]
    dropped = [c["name"] for c in cands if looks_public(c)]
    log("filter", "dropped_public_or_acquired", dropped)
    return kept


# ---------------------------------------------------------------- 4. RANKER
def ranker(category, candidates):
    if not candidates:
        return []
    pool = sorted(candidates, key=lambda c: -c.get("mentions", 1))[:25]
    brief = [{k: c.get(k) for k in ("name", "what_it_does", "total_funding", "valuation",
                                    "latest_news", "mentions")} for c in pool]
    out = llm_json(
        "You rate startups. Reply as JSON: {\"ranking\": [{\"name\", \"score\", \"reason\"}]}. "
        "score is 1-10 for growth momentum and recency of news only.",
        f"Category: {category}\nCandidates:\n{json.dumps(brief)}")
    rated = {str(r.get("name", "")).lower().strip(): r
             for r in out.get("ranking", []) if isinstance(r, dict)}
    for c in pool:
        r = rated.get(c["name"].lower().strip(), {})
        try:
            llm = max(0.0, min(float(r.get("score", 0)), 10.0))
        except (TypeError, ValueError):
            llm = 0.0
        c["valuation_usd"] = parse_money(c.get("valuation"))
        c["funding_usd"] = parse_money(c.get("total_funding"))
        c["llm_score"] = llm
        c["reason"] = r.get("reason", "")
        c["score"] = round(composite(c["valuation_usd"], c["funding_usd"], llm, c.get("mentions", 1)), 1)
    ranked = sorted(pool, key=lambda c: -c["score"])
    log("ranker", "ranked", [c["name"] for c in ranked[:10]])
    return ranked


# ---------------------------------------------------------------- 5. ENRICHER
def enricher(category, top):
    for c in top:
        c.setdefault("sources", [])
        need_news = is_unknown(c.get("latest_news"))
        need_money = is_unknown(c.get("total_funding")) or is_unknown(c.get("valuation"))
        if not (need_news or need_money):
            continue
        results = news_search(f"{c['name']} {category} funding valuation {YEAR}", 5)
        if not results:
            continue
        if need_news:
            r = results[0]
            date = (r.get("date") or "")[:10]
            c["latest_news"] = f"{r['title']} ({date})" if date else r["title"]
            if r.get("url") and r["url"] not in c["sources"]:
                c["sources"].append(r["url"])
        if need_money:
            text = "\n".join(f"{r['title']}. {r['snippet']}" for r in results)[:3000]
            out = llm_json(
                "Extract facts about ONE company. Reply as JSON: {\"total_funding\", \"valuation\"}. "
                "total_funding = total raised; valuation = latest valuation; different numbers. "
                "Use \"unknown\" if not stated. Never invent.",
                f"Company: {c['name']}\nText:\n{text}")
            for f in ("total_funding", "valuation"):
                v = out.get(f)
                if is_unknown(c.get(f)) and not is_unknown(v):
                    c[f] = str(v)
            if (not is_unknown(c.get("total_funding"))
                    and str(c["total_funding"]).strip().lower() == str(c.get("valuation", "")).strip().lower()):
                c["total_funding"] = UNKNOWN
        c["valuation_usd"] = parse_money(c.get("valuation"))
        c["funding_usd"] = parse_money(c.get("total_funding"))
        c["score"] = round(composite(c["valuation_usd"], c["funding_usd"],
                                     c.get("llm_score", 0), c.get("mentions", 1)), 1)
    top = sorted(top, key=lambda c: -c.get("score", 0))
    log("enricher", "enriched", [c["name"] for c in top])
    return top


# ---------------------------------------------------------------- 6. CRITIC
def critic(top):
    issues = []
    if len(top) < 10:
        issues.append(f"only {len(top)} startups")
    for c in top:
        n = c["name"]
        if not c.get("sources"):
            issues.append(f"{n}: no source")
        if looks_public(c):
            issues.append(f"{n}: looks like a public company")
        if is_unknown(c.get("latest_news")):
            issues.append(f"{n}: no latest news")
        f, v = c.get("total_funding"), c.get("valuation")
        if is_unknown(f) and is_unknown(v):
            issues.append(f"{n}: no funding or valuation")
        elif not is_unknown(f) and str(f).strip().lower() == str(v).strip().lower():
            issues.append(f"{n}: funding equals valuation")
    log("critic", "verdict", "OK" if not issues else issues)
    return issues


# ---------------------------------------------------------------- 7. REPORTER
def _cell(x):
    return str(x if x is not None else "").replace("|", "/").replace("\n", " ")


def reporter(category, top, outdir="outputs", warnings=None):
    os.makedirs(outdir, exist_ok=True)
    slug = re.sub(r"\W+", "_", category.lower())
    lines = [f"# Top 10 {category} Startups ({datetime.date.today()})\n",
             "| # | Startup | What it does | Total funding | Valuation | Status | Latest news | Score |",
             "|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(top, 1):
        lines.append(f"| {i} | {_cell(c['name'])} | {_cell(c.get('what_it_does'))} | "
                     f"{_cell(c.get('total_funding'))} | {_cell(c.get('valuation'))} | "
                     f"{_cell(c.get('status'))} | {_cell(c.get('latest_news'))} | {c.get('score', 0):.1f} |")
    lines.append("\n## Sources")
    for i, c in enumerate(top, 1):
        lines.append(f"{i}. {c['name']}: " + ", ".join(c.get("sources", [])[:3]))
    if warnings:
        lines.append("\n## Data quality warnings")
        lines += [f"- {w}" for w in warnings]
    md = f"{outdir}/{slug}_top10.md"
    open(md, "w").write("\n".join(lines))
    json.dump(top, open(f"{outdir}/{slug}_top10.json", "w"), indent=2)
    log("reporter", "wrote", md)
    return md
