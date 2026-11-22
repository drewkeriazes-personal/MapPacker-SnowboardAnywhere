"""FEAT-348: has the OpenStreetMap data in a raw folder been edited since it was fetched? One small Overpass request
answers it for all the osm/ items at once, so a rebuild fetches OSM again only when it changed.

The request is each item's own query (from the manifest item's url or body, as gen_manifest.py writes it) with
`(newer:"<the item's fetch time>")` on every statement and `out count;` for its output, the items one after the
other:

    [out:json][timeout:45];(way["piste:type"](bbox)(newer:"2026-11-08T10:00:00Z");node[...](bbox)(newer:...););out count;
    (... the next item ...);out count;

Overpass answers one `count` element per `out count;`, in order: a total above 0 means that item has elements added
or edited since its fetch. `newer:` compares an element's own timestamp, so it can't see a deleted element (or a
way whose nodes moved but whose own version didn't change): fetch_index.MAX_AGE_DAYS is the backstop for those.

The hosts are the item's url and then its alts, the order fetch.ps1 tries them in, each tried once, all within
BUDGET_S (a host that hangs gets its share of it). check() raises CheckFailed on any trouble (no host answered, an error, an answer it can't read), and the
caller keeps the cached copy: the check never fails a build."""
import json
import re
import time
import urllib.parse
import urllib.request

BUDGET_S = 60
PREFIX = "osm/"
STATEMENT = re.compile(r"(node|way|rel|relation|nwr|nw|nr|wr|area)\b")


class CheckFailed(Exception):
    pass


def query_of(item: dict) -> str:
    """the Overpass QL a manifest item asks for (the `data` parameter of its url, or of its body when it posts)"""
    data = urllib.parse.parse_qs(item["body"] if item.get("body") else urllib.parse.urlsplit(item["url"]).query)
    if not data.get("data"):
        raise CheckFailed(f"{item['path']}: no Overpass query in the manifest item")
    return data["data"][0]


def split(text: str) -> list[str]:
    """the statements of `text` split at each ; outside quotes and parentheses"""
    out, cur, depth, quote, esc = [], [], 0, None, False
    for ch in text:
        if quote:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == ";" and depth == 0:
            if "".join(cur).strip():
                out.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip() or depth or quote:
        raise CheckFailed(f"unreadable Overpass query: {text[:80]!r}")
    return out


def statements(q: str) -> list[str]:
    """the query statements of one item's query: its settings and its out statement left out, unions opened"""
    out = []
    for part in split(q):
        if part.startswith("[") or re.match(r"out\b", part):
            continue
        if part.startswith("(") and part.endswith(")"):
            out += statements(part[1:-1])
        elif STATEMENT.match(part) and "->" not in part:
            out.append(part)
        else:
            raise CheckFailed(f"a statement the check can't filter: {part[:80]!r}")
    return out


def check_query(queries: list[tuple[str, str]], timeout: int) -> str:
    """[(item query, fetched time)] -> one query with a count for each, in order"""
    body = "".join("(" + "".join(f'{s}(newer:"{since}");' for s in statements(q)) + ");out count;"
                   for q, since in queries)
    return f"[out:json][timeout:{timeout}];" + body


def hosts(item: dict) -> list[str]:
    """the interpreter URLs fetch.ps1 would try, in its order"""
    return list(dict.fromkeys(u.split("?")[0] for u in [item["url"], *item.get("alts", [])]))


def send(base: str, query: str, timeout: float) -> bytes:
    """GET, as the fetch does (.NET's POST sends Expect: 100-continue, which Overpass rejects)"""
    from resort import UA
    req = urllib.request.Request(base + "?data=" + urllib.parse.quote(query, safe=""), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def counts(answer: bytes, n: int) -> list[int]:
    try:
        d = json.loads(answer)
        got = [int(e["tags"]["total"]) for e in d["elements"] if e.get("type") == "count"]
    except (ValueError, KeyError, TypeError, AttributeError):
        raise CheckFailed(f"an answer that isn't Overpass JSON: {answer[:80]!r}") from None
    if len(got) != n:
        raise CheckFailed(f"{len(got)} counts for {n} queries" + (f" ({d['remark'][:120]})" if d.get("remark") else ""))
    return got


def check(items: list[dict], since: dict, sender=send, budget=BUDGET_S, clock=time.monotonic) -> dict:
    """{path: elements added or edited since since[path]} for the manifest items, one request; raises CheckFailed"""
    query = check_query([(query_of(i), since[i["path"]]) for i in items], max(10, int(budget) - 15))
    end, errors, urls = clock() + budget, [], hosts(items[0])
    for k, base in enumerate(urls):
        left = end - clock()
        if left < 1:
            errors.append("out of time")
            break
        try:     # a host that hangs leaves time for the ones after it
            answer = sender(base, query, left / (len(urls) - k))
            return dict(zip((i["path"] for i in items), counts(answer, len(items))))
        except Exception as e:   # noqa: BLE001  anything at all: the next host, then keep the cached copy
            errors.append(f"{urllib.parse.urlsplit(base).hostname}: {str(e)[:160]}")
    raise CheckFailed("; ".join(errors))
