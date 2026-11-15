#!/usr/bin/env python3
"""Builds the Abla IA static site (abla.co), WhatsApp first.
Outputs:
  ../docs/     the website itself (no preview banner), ready for GitHub Pages
  ../preview/  the same pages with a preview banner, for the claude.ai preview
Run: python3 src/build.py
Texts live in content_es.py (master), content_en.py, content_pt.py and content_fr.py, all with the same structure.
Facts only from the owner; anything still unknown is a {{PH:...}} placeholder, shown as a yellow marker and listed in PLACEHOLDERS.txt.
"""
import hashlib, html, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import content_es, content_en, content_pt, content_fr

# ---------------- Settings ----------------
SITE = "https://abla.co"
# GitHub Pages custom domain. Empty = the site answers on cbsbcreations.github.io/abla-site/ only;
# "abla.co" = the build writes docs/CNAME and GitHub serves the site on abla.co (set once DNS points at GitHub).
CUSTOM_DOMAIN = ""
LANGS = ["es", "pt", "en", "fr"]          # order of the language switch
DEFAULT = "es"                             # the root address and x-default
D = {"es": content_es.D, "pt": content_pt.D, "en": content_en.D, "fr": content_fr.D}

# Contact details still to come from the owner. Empty = the site shows a visible "to fill in" marker, and the WhatsApp buttons
# go to the contact page instead of a dead link.
WA_NUMBER = ""      # Abla's WhatsApp number, digits only with country code, e.g. "573001234567"
WA_DISPLAY = ""     # the same number as shown on the site, e.g. "+57 300 123 4567"
EMAIL = ""          # e.g. "hola@abla.co"

# Prices in Colombian pesos (Nov 2026)
PRICE = {"wa": 279000, "setup": 349000, "resv_addon": 34900, "resv_only": 139000, "lang": 34900}

PRODUCTS = ["whatsapp", "phone", "webshop", "kiosk"]
SECTORS = ["rapidas", "pizzeria", "burger", "asadero", "sushi", "todos"]
PAGES = ["home"] + PRODUCTS + ["pricing"] + SECTORS + ["about", "contact", "legal"]

FONTS = ("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700"
         "&family=Figtree:ital,wght@0,400;0,500;0,600;0,700;1,500&family=JetBrains+Mono:wght@500;700&display=swap")
PLACEHOLDERS = {}

# ---------------- Helpers ----------------
def e(s):
    return html.escape(str(s), quote=True)

def T(lang):
    return D[lang]

def ph(text, lang, page=""):
    """{{PH:...}} becomes a visible marker; everything else is escaped."""
    out, pos = [], 0
    for m in re.finditer(r"\{\{PH:(.*?)\}\}", text):
        out.append(e(text[pos:m.start()]))
        out.append(f'<mark class="ph">[{e(T(lang)["UI"]["ph"])}: {e(m.group(1))}]</mark>')
        PLACEHOLDERS.setdefault((lang, m.group(1)), set()).add(page)
        pos = m.end()
    out.append(e(text[pos:]))
    return "".join(out)

def rich(text, lang, page=""):
    return ph(text, lang, page).replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")

def plain(text):
    return re.sub(r"<[^>]+>", "", re.sub(r"\{\{PH:.*?\}\}", "", text)).strip()

def cop(n, lang):
    """A peso amount in the page language's style: $279.000 (es), COP 279.000 (pt), COP 279,000 (en), 279 000 COP (fr).
    Outside Spanish the currency is written out, so nobody reads the $ as dollars or reais."""
    if lang == "es": return "$" + f"{n:,}".replace(",", ".")
    if lang == "pt": return "COP\u00a0" + f"{n:,}".replace(",", ".")
    if lang == "en": return "COP\u00a0" + f"{n:,}"
    return f"{n:,}".replace(",", " ") + " COP"

def fill(text, lang):
    """Prices in the texts are written as {wa}, {setup}, {resv_addon}, {resv_only}, {lang}."""
    return re.sub(r"\{(wa|setup|resv_addon|resv_only|lang)\}", lambda m: cop(PRICE[m.group(1)], lang), text)

def path_of(lang, pid):
    return f"{lang}/{T(lang)['SLUGS'][pid]}.html"

def canonical(lang, pid):
    s = T(lang)["SLUGS"][pid]
    return f"{SITE}/{lang}/" + ("" if s == "index" else s)

def wa_href(lang, prefix):
    return f"https://wa.me/{WA_NUMBER}" if WA_NUMBER else prefix + path_of(lang, "contact") + "#whatsapp"

def name_of(lang, pid):
    t = T(lang)
    if pid in PRODUCTS: return t["P"][pid]["name"]
    if pid in SECTORS: return t["S"][pid]["nav"]
    return {"home": t["UI"]["home"], "pricing": t["UI"]["pricing"], "about": t["UI"]["about"],
            "contact": t["UI"]["contact"], "legal": t["UI"]["foot_legal"]}[pid]

def meta_of(lang, pid):
    t = T(lang)
    if pid in PRODUCTS: d = t["P"][pid]
    elif pid in SECTORS: d = t["S"][pid]
    else: d = {"home": t["HOME"], "pricing": t["PRICING"], "about": t["ABOUT"], "contact": t["CONTACT"], "legal": t["LEGAL"]}[pid]
    return fill(d["title"], lang), fill(d["desc"], lang)

# ---------------- JSON-LD ----------------
def org():
    o = {"@type": "Organization", "@id": SITE + "/#org", "name": "Abla IA", "url": SITE + "/",
         "description": "WhatsApp AI that takes restaurant orders and reservations 24/7, plus phone AI, online store with QR ordering and self-order kiosk. Colombia.",
         "areaServed": "CO"}
    if WA_NUMBER:
        o["contactPoint"] = {"@type": "ContactPoint", "telephone": "+" + WA_NUMBER, "contactType": "sales", "availableLanguage": ["es", "pt", "en", "fr"]}
    if EMAIL: o["email"] = EMAIL
    return o

def jsonld(lang, pid, faqs, crumbs):
    title, desc = meta_of(lang, pid)
    graph = [org(), {"@type": "WebPage", "@id": canonical(lang, pid) + "#page", "url": canonical(lang, pid), "name": title,
                     "description": desc, "inLanguage": T(lang)["HTML_LANG"],
                     "isPartOf": {"@type": "WebSite", "name": "Abla IA", "url": SITE + "/"}, "publisher": {"@id": SITE + "/#org"}}]
    if crumbs:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]})
    if pid in PRODUCTS:
        d = T(lang)["P"][pid]
        prod = {"@type": "Product", "name": "Abla IA " + d["name"], "description": fill(d["desc"], lang),
                "brand": {"@type": "Brand", "name": "Abla IA"}, "url": canonical(lang, pid)}
        if pid == "whatsapp":
            prod["offers"] = [{"@type": "Offer", "price": str(PRICE["wa"]), "priceCurrency": "COP",
                               "priceSpecification": {"@type": "UnitPriceSpecification", "price": str(PRICE["wa"]), "priceCurrency": "COP", "billingDuration": "P1M"}}]
        graph.append(prod)
    good = [(fill(q, lang), fill(a, lang)) for q, a in faqs if "{{PH:" not in a]
    if good:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in good]})
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/") + "</script>"

# ---------------- Logo ----------------
# The Abla mark: a speech bubble with three typing dots (Abla comes from "habla", talk). Yellow; the dots take the page colour.
LOGO_MARK = ('<svg class="logo-mark" viewBox="0 0 24 24" aria-hidden="true">'
             '<path class="lm-b" d="M7.2 2.5h9.6a5.2 5.2 0 0 1 5.2 5.2v4.6a5.2 5.2 0 0 1-5.2 5.2h-6.3l-4.7 3.9a.75.75 0 0 1-1.23-.58v-3.6A5.2 5.2 0 0 1 2 12.3V7.7a5.2 5.2 0 0 1 5.2-5.2z"/>'
             '<circle class="lm-d" cx="7.9" cy="10" r="1.55"/><circle class="lm-d" cx="12" cy="10" r="1.55"/><circle class="lm-d" cx="16.1" cy="10" r="1.55"/></svg>')
def logo_html(href, label=""):
    al = f' aria-label="{e(label)}"' if label else ""
    return f'<a class="logo" href="{href}"{al}>{LOGO_MARK}<span class="logo-word">Abla<sup>IA</sup></span></a>'

ASSET_Q = {"css": "", "js": "", "scenes": ""}
def asset_fingerprint(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]

# ---------------- Head, header, footer ----------------
def head(lang, pid, prefix, faqs, crumbs):
    title, desc = meta_of(lang, pid)
    t = T(lang)
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{canonical(l, pid)}">' for l in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{canonical(DEFAULT, pid)}">'
    parts = [f"<title>{e(title)}</title>", f'<meta name="description" content="{e(desc)}">',
             f'<link rel="canonical" href="{canonical(lang, pid)}">', alts,
             '<meta property="og:type" content="website">', '<meta property="og:site_name" content="Abla IA">',
             f'<meta property="og:title" content="{e(title)}">', f'<meta property="og:description" content="{e(desc)}">',
             f'<meta property="og:url" content="{canonical(lang, pid)}">', f'<meta property="og:locale" content="{t["OG_LOCALE"]}">',
             '<meta name="twitter:card" content="summary_large_image">', '<meta name="theme-color" content="#000000">',
             f'<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png">',
             '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
             f'<link rel="stylesheet" href="{FONTS}">',
             f'<link rel="stylesheet" href="{prefix}assets/site.css{ASSET_Q["css"]}">',
             f'<link rel="stylesheet" href="{prefix}assets/scenes.css{ASSET_Q["scenes"]}">',
             jsonld(lang, pid, faqs, crumbs)]
    return "\n".join(parts)

def header(lang, pid, prefix):
    t, u = T(lang), T(lang)["UI"]
    h = lambda p: prefix + path_of(lang, p)
    cur = lambda p: ' aria-current="page"' if p == pid else ""
    def prod_link(p):
        star = f'<span class="nav-tag">{e(u["main"])}</span>' if p == "whatsapp" else ""
        return f'<a href="{h(p)}"{cur(p)}>{e(t["P"][p]["name"])}{star}<small>{e(t["P"][p]["sub"])}</small></a>'
    prod_links = "".join(prod_link(p) for p in PRODUCTS)
    sec_links = "".join(f'<a href="{h(s)}"{cur(s)}>{e(t["S"][s]["name"])}</a>' for s in SECTORS)
    langs = "".join(f'<a href="{prefix + path_of(l, pid)}" hreflang="{l}" lang="{l}" title="{e(T(l)["LANG_NAME"])}"{" aria-current=\"true\"" if l == lang else ""}>{l}</a>' for l in LANGS)
    mob_prod = "".join(f'<a href="{h(p)}">{e(t["P"][p]["name"])}</a>' for p in PRODUCTS)
    mob_sec = "".join(f'<a href="{h(s)}">{e(t["S"][s]["name"])}</a>' for s in SECTORS)
    return f'''<header class="site-header"><div class="wrap">
{logo_html(h("home"), "Abla IA")}
<nav class="nav" aria-label="{e(u["nav_label"])}">
<a class="nav-wa" href="{h("whatsapp")}"{cur("whatsapp")}>{e(t["P"]["whatsapp"]["name"])}</a>
<details class="dd"><summary>{e(u["products"])}</summary><div class="dd-menu">{prod_links}</div></details>
<details class="dd"><summary>{e(u["sectors"])}</summary><div class="dd-menu">{sec_links}</div></details>
<a href="{h("pricing")}"{cur("pricing")}>{e(u["pricing"])}</a>
<a href="{h("about")}"{cur("about")}>{e(u["about"])}</a>
<a href="{h("contact")}"{cur("contact")}>{e(u["contact"])}</a>
<div class="lang" aria-label="{e(u["lang_label"])}">{langs}</div>
</nav>
<a class="btn btn-primary btn-head" href="{h("contact")}">{e(u["demo"])}</a>
<details class="mobile-menu"><summary>{e(u["menu"])}</summary><div class="mobile-panel">
<span class="group-label">{e(u["products"])}</span>{mob_prod}
<span class="group-label">{e(u["sectors"])}</span>{mob_sec}
<span class="group-label">Abla IA</span>
<a href="{h("pricing")}">{e(u["pricing"])}</a><a href="{h("about")}">{e(u["about"])}</a><a href="{h("contact")}">{e(u["demo"])}</a>
<div class="lang" style="margin-top:12px">{langs}</div>
</div></details>
</div></header>'''

def footer(lang, prefix, page):
    t, u = T(lang), T(lang)["UI"]
    h = lambda p: prefix + path_of(lang, p)
    prods = "".join(f'<li><a href="{h(p)}">{e(t["P"][p]["name"])}</a></li>' for p in PRODUCTS)
    secs = "".join(f'<li><a href="{h(s)}">{e(t["S"][s]["name"])}</a></li>' for s in SECTORS)
    wa = (f'<a href="{wa_href(lang, prefix)}" rel="noopener">{e(WA_DISPLAY)}</a>' if WA_NUMBER
          else ph("{{PH:" + u["ph_wa"] + "}}", lang, page))
    return f'''<footer class="site-footer"><div class="wrap"><div class="foot-mark" aria-hidden="true">Abla</div>
<div class="foot-cols">
<div style="display:grid;gap:12px;align-content:start">{logo_html(h("home"))}<p>{e(u["foot_tag"])}</p><p>WhatsApp: {wa}</p></div>
<div><h4>{e(u["products"])}</h4><ul>{prods}</ul></div>
<div><h4>{e(u["sectors"])}</h4><ul>{secs}</ul></div>
<div><h4>Abla IA</h4><ul><li><a href="{h("pricing")}">{e(u["pricing"])}</a></li><li><a href="{h("about")}">{e(u["about"])}</a></li><li><a href="{h("contact")}">{e(u["contact"])}</a></li><li><a href="{h("legal")}">{e(u["foot_legal"])}</a></li></ul></div>
</div>
<div class="foot-bottom"><span>{ph(u["foot_company"], lang, page)}</span><span>{e(u["foot_rights"])}</span></div>
</div></footer>'''

# ---------------- Scenes: WhatsApp ----------------
CHECKS = '<svg viewBox="0 0 18 12" aria-hidden="true"><path d="M1 6.5l3 3L10 2.5M7 9.5l1 1L15 2.5"/></svg>'
ICON_BACK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>'
ICON_VIDEO = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="6" width="13" height="12" rx="2.5"/><path d="M15.5 10.5l6-3.5v10l-6-3.5z"/></svg>'
ICON_CALL = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3.5h3.5l2 5-2.5 1.5a11 11 0 0 0 6 6l1.5-2.5 5 2V19a2 2 0 0 1-2 2A17 17 0 0 1 3 5.5a2 2 0 0 1 2-2z"/></svg>'
ICON_MIC = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/></svg>'

# Timelines of the chat scenes, in seconds. Each item: kind, when it appears, and for the restaurant's (AI) messages when the
# typing dots start. "order": customer, AI, reply buttons, customer taps the first button, AI. "qa": customer, AI, customer, AI.
# The keyframes are written to assets/scenes.css by scenes_css(). Without motion every message simply shows.
TL = {
    "order": {"T": 14.0, "tap": 6.0, "items": [("out", 1.0, None), ("in", 3.4, 1.7), ("btns", 4.0, None), ("out", 6.4, None), ("in", 8.6, 7.1)]},
    "qa":    {"T": 13.0, "tap": None, "items": [("out", 1.0, None), ("in", 3.3, 1.7), ("out", 5.9, None), ("in", 8.2, 6.6)]},
}

def wa_chat(lang, scene, tl="order", big=False, shop=None):
    """A phone with a WhatsApp chat, seen by the customer: the customer's messages on the right (green), the restaurant's
    AI on the left (white), WhatsApp reply buttons, typing dots and "typing..." in the header. scene = dict with "msgs"
    (texts in timeline order; the buttons item is a pair) and "times"."""
    sc = T(lang)["SC"]
    spec = TL[tl]
    msgs, times = scene["msgs"], scene["times"]
    slots, ti = [], 0
    for i, ((kind, _at, typing), m) in enumerate(zip(spec["items"], msgs), 1):
        if kind == "btns":
            b1, b2 = m
            slots.append(f'<div class="wap-btns wm{i}"><span class="wap-b1">{e(b1)}<u class="wap-tap"></u></span><span>{e(b2)}</span></div>')
            continue
        tm = times[ti]; ti += 1
        if kind == "out":
            slots.append(f'<div class="wap-slot wap-so wm{i}"><div class="wap-m wap-out"><p>{e(m)}</p><span class="wap-meta">{e(tm)}<i class="wap-ticks">{CHECKS}</i></span></div></div>')
        else:
            slots.append(f'<div class="wap-slot wap-si wm{i}"><span class="wap-dots wd{i}" aria-hidden="true"><i></i><i></i><i></i></span>'
                         f'<div class="wap-m wap-in"><p>{e(m)}</p><span class="wap-meta">{e(tm)}</span></div></div>')
    name = shop or sc["shop"]
    initials = "".join(w[0] for w in name.split()[:2]).upper()
    status = f'<small class="wap-st"><span class="wap-on">{e(sc["online"])}</span><span class="wap-typ">{e(sc["typing"])}</span></small>'
    return (f'<div class="wap{" wap-big" if big else ""}" data-tl="{tl}" role="img" aria-label="{e(T(lang)["UI"]["example"])}: WhatsApp">'
            f'<div class="wap-phone"><div class="wap-scr">'
            f'<div class="wap-bar"><i class="wap-ic">{ICON_BACK}</i><span class="wap-av">{e(initials)}</span>'
            f'<span class="wap-who"><b>{e(name)}</b>{status}</span><i class="wap-ic">{ICON_VIDEO}</i><i class="wap-ic">{ICON_CALL}</i></div>'
            f'<div class="wap-body"><span class="wap-day">{e(sc["today"])}</span>{"".join(slots)}</div>'
            f'<div class="wap-input"><span>{e(sc["input"])}</span><i>{ICON_MIC}</i></div>'
            f'</div></div></div>')

IB_T = 12.0
IB_N = 8                                         # chats in the list
IB_AT = [1.8 + i * 0.78 for i in range(IB_N)]    # when each chat gets its answer
IB_FROM = 52 - IB_N                              # the counter ends on 52
def inbox(lang):
    """The 50+ scene: a WhatsApp chat list full of unread customer messages; one after the other the AI answers them
    (the green badge goes, the last line becomes the AI's answer with blue ticks) and the counter on top goes up."""
    sc = T(lang)["SC"]["inbox"]
    hues = [32, 198, 340, 150, 265, 12, 222, 95]
    rows = ""
    for i, (name, cust, ai, tm, n) in enumerate(sc["rows"]):
        ini = "".join(w[0] for w in name.replace("+", "").split()[:2]).upper() if not name.startswith("+") else "#"
        rows += (f'<div class="ib-row ib{i}"><span class="ib-av" style="--h:{hues[i]}">{e(ini)}</span>'
                 f'<div class="ib-mid"><b>{e(name)}</b><span class="ib-prev"><span class="ib-c">{e(cust)}</span>'
                 f'<span class="ib-a"><i class="wap-ticks">{CHECKS}</i>{e(ai)}</span></span></div>'
                 f'<div class="ib-end"><small class="ib-time">{e(tm)}</small><span class="ib-badge">{n}</span></div></div>')
    roll = '<span class="ib-roll"><span>' + "".join(f"<em>{IB_FROM + k}</em>" for k in range(IB_N + 1)) + "</span></span>"
    return (f'<div class="wap wib" role="img" aria-label="{e(T(lang)["UI"]["example"])}: WhatsApp">'
            f'<div class="wap-phone"><div class="wap-scr">'
            f'<div class="wap-bar ib-bar"><b class="ib-title">{e(sc["title"])}</b><span class="ib-chip"><i></i>{e(sc["badge"])}</span></div>'
            f'<div class="ib-count">{roll}<span>{e(sc["count_label"])}</span></div>'
            f'<div class="ib-list">{rows}</div>'
            f'</div></div></div>')

def pct(x, total):
    return f"{x / total * 100:.2f}%"

def scenes_css():
    """Keyframes for the chat timelines and the inbox, worked out from TL / IB_AT."""
    out = ["/* Generated by build.py from the scene timelines. Do not edit by hand. */"]
    for name, spec in TL.items():
        Tt = spec["T"]; end = Tt - 0.7
        sel = f'.wap[data-tl="{name}"]'
        out.append(f"{sel} {{ --t: {Tt}s; }}")
        windows = []
        for i, (kind, at, typing) in enumerate(spec["items"], 1):
            a0, a1, a2 = pct(max(at - 0.01, 0), Tt), pct(at + 0.45, Tt), pct(end, Tt)
            target = f"{sel} .wm{i}" + (" > .wap-m" if kind in ("out", "in") else "")
            out.append(f"@keyframes wap-{name}-m{i} {{ 0%, {a0} {{ opacity: 0; transform: translateY(1.6cqi) scale(.96); }} "
                       f"{a1}, {a2} {{ opacity: 1; transform: none; }} 100% {{ opacity: 0; transform: none; }} }}")
            out.append(f"{target} {{ animation: wap-{name}-m{i} var(--t) var(--ease) infinite both; }}")
            if kind == "in" and typing is not None:
                windows.append((typing, at))
                out.append(f"@keyframes wap-{name}-d{i} {{ 0%, {pct(typing, Tt)} {{ opacity: 0; }} {pct(typing + 0.15, Tt)}, {pct(at - 0.05, Tt)} {{ opacity: 1; }} "
                           f"{pct(at + 0.05, Tt)}, 100% {{ opacity: 0; }} }}")
                out.append(f"{sel} .wd{i} {{ animation: wap-{name}-d{i} var(--t) linear infinite both; }}")
        # "typing..." in the header during the typing windows, "online" otherwise
        frames_t, frames_o = ["0% { opacity: 0; }"], ["0% { opacity: 1; }"]
        for a, b in windows:
            frames_t += [f"{pct(a, Tt)} {{ opacity: 0; }}", f"{pct(a + 0.12, Tt)}, {pct(b, Tt)} {{ opacity: 1; }}", f"{pct(b + 0.12, Tt)} {{ opacity: 0; }}"]
            frames_o += [f"{pct(a, Tt)} {{ opacity: 1; }}", f"{pct(a + 0.12, Tt)}, {pct(b, Tt)} {{ opacity: 0; }}", f"{pct(b + 0.12, Tt)} {{ opacity: 1; }}"]
        frames_t.append("100% { opacity: 0; }"); frames_o.append("100% { opacity: 1; }")
        out.append(f"@keyframes wap-{name}-typ {{ {' '.join(frames_t)} }}")
        out.append(f"@keyframes wap-{name}-on {{ {' '.join(frames_o)} }}")
        out.append(f"{sel} .wap-typ {{ animation: wap-{name}-typ var(--t) linear infinite both; }} {sel} .wap-on {{ animation: wap-{name}-on var(--t) linear infinite both; }}")
        if spec["tap"]:
            tp = spec["tap"]
            out.append(f"@keyframes wap-{name}-tap {{ 0%, {pct(tp, Tt)} {{ opacity: 0; transform: scale(.2); }} {pct(tp + 0.1, Tt)} {{ opacity: .55; }} "
                       f"{pct(tp + 0.7, Tt)}, 100% {{ opacity: 0; transform: scale(2.4); }} }}")
            out.append(f"@keyframes wap-{name}-press {{ 0%, {pct(tp, Tt)} {{ background-color: #fff; }} {pct(tp + 0.1, Tt)}, {pct(tp + 0.6, Tt)} {{ background-color: #E3F3FB; }} "
                       f"{pct(tp + 0.9, Tt)}, 100% {{ background-color: #fff; }} }}")
            out.append(f"{sel} .wap-tap {{ animation: wap-{name}-tap var(--t) ease-out infinite both; }} {sel} .wap-b1 {{ animation: wap-{name}-press var(--t) linear infinite both; }}")
    # the hero: the kitchen ticket prints once the order is confirmed (same loop as "order")
    Tt = TL["order"]["T"]; done = TL["order"]["items"][-1][1] + 0.5
    out.append(f"@keyframes sw-print {{ 0%, {pct(done, Tt)} {{ opacity: 0; transform: translateY(-14%) rotate(4deg); clip-path: inset(0 0 100% 0); }} "
               f"{pct(done + 1.2, Tt)}, {pct(Tt - 0.7, Tt)} {{ opacity: 1; transform: translateY(0) rotate(4deg); clip-path: inset(0 0 0 0); }} 100% {{ opacity: 0; transform: translateY(0) rotate(4deg); clip-path: inset(0 0 0 0); }} }}")
    # inbox
    Ti = IB_T; endi = Ti - 0.7
    out.append(f".wib {{ --t: {Ti}s; }}")
    for i, at in enumerate(IB_AT):
        pop = 0.25 + i * 0.12
        out.append(f"@keyframes ib-c{i} {{ 0%, {pct(at, Ti)} {{ opacity: 1; }} {pct(at + 0.3, Ti)}, {pct(endi, Ti)} {{ opacity: 0; }} 100% {{ opacity: 1; }} }}")
        out.append(f"@keyframes ib-a{i} {{ 0%, {pct(at, Ti)} {{ opacity: 0; transform: translateY(40%); }} {pct(at + 0.35, Ti)}, {pct(endi, Ti)} {{ opacity: 1; transform: none; }} 100% {{ opacity: 0; transform: none; }} }}")
        out.append(f"@keyframes ib-b{i} {{ 0%, {pct(pop, Ti)} {{ transform: scale(0); }} {pct(pop + 0.25, Ti)}, {pct(at, Ti)} {{ transform: scale(1); }} {pct(at + 0.25, Ti)}, 100% {{ transform: scale(0); }} }}")
        out.append(f"@keyframes ib-t{i} {{ 0%, {pct(at, Ti)} {{ color: #1FAF5A; font-weight: 600; }} {pct(at + 0.2, Ti)}, 100% {{ color: #667781; font-weight: 400; }} }}")
        out.append(f"@keyframes ib-r{i} {{ 0%, {pct(at, Ti)} {{ background: #F0FBF4; }} {pct(at + 0.6, Ti)}, 100% {{ background: #fff; }} }}")
        out.append(f".wib .ib{i} .ib-c {{ animation: ib-c{i} var(--t) linear infinite both; }} .wib .ib{i} .ib-a {{ animation: ib-a{i} var(--t) var(--ease) infinite both; }} "
                   f".wib .ib{i} .ib-badge {{ animation: ib-b{i} var(--t) var(--ease) infinite both; }} .wib .ib{i} .ib-time {{ animation: ib-t{i} var(--t) linear infinite both; }} "
                   f".wib .ib{i} {{ animation: ib-r{i} var(--t) linear infinite both; }}")
    n1 = IB_N + 1
    step = lambda k: f"translateY(-{k / n1 * 100:.4f}%)"
    frames = [f"0% {{ transform: {step(0)}; }}"]
    for k, at in enumerate(IB_AT, 1):
        frames.append(f"{pct(at, Ti)} {{ transform: {step(k - 1)}; }}")
        frames.append(f"{pct(at + 0.3, Ti)} {{ transform: {step(k)}; }}")
    frames.append(f"{pct(endi, Ti)} {{ transform: {step(IB_N)}; }} 100% {{ transform: {step(IB_N)}; }}")
    out.append(f".wib .ib-roll > span {{ transform: {step(IB_N)}; }}")
    out.append(f"@keyframes ib-roll {{ {' '.join(frames)} }}")
    out.append(".wib .ib-roll > span { animation: ib-roll var(--t) var(--ease) infinite both; }")
    out.append("@media (prefers-reduced-motion: reduce) { .wap *, .wap *::before, .wap *::after, .sw-ticket .ticket { animation: none !important; } "
               ".wap .wap-dots, .wap .wap-typ, .wap .wap-tap, .wib .ib-c, .wib .ib-badge { display: none; } "
               "}")
    return "\n".join(out) + "\n"

# ---------------- Scenes: ticket, phone AI, online store, kiosk, restaurant types ----------------
def ticket_i(lang, items, channel, when):
    u = T(lang)["UI"]
    lis = "".join(f'<li class="sub">{e(t)}</li>' if not q else f'<li><span>{e(q)}</span>{e(t)}</li>' for q, t in items)
    return f'''<div class="ticket" role="img" aria-label="{e(u["example"])}: {e(u["ticket_label"])}">
<div class="t-head"><span>ABLA</span><span>#1042</span></div>
<div class="t-meta"><span>{e(channel)}</span><span>{e(when)}</span></div>
<ul>{lis}</ul>
<div class="t-foot"><span>{e(u["example"])}</span><span>{e(T(lang)["SC"]["ticket_time"])}</span></div>
</div>'''

def home_ticket(lang):
    sc = T(lang)["SC"]
    return ticket_i(lang, sc["ticket_items"], *sc["ticket_meta"])

PS_TIMER = ["00:02", "00:05", "00:09", "00:14", "00:18"]
def phone_scene_i(lang):
    """Animated scene for the phone AI (same three parts as on conveasy.be, one 17 s loop; see .pscene in site.css):
    the counter with the ringing desk phone, the call with the AI's voice orb and the words, then the laptop with the new order
    and the printer printing the ticket."""
    sc = T(lang)["SC"]; t = sc["pcall"]
    ring, picked = sc["call"]
    check = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
    bell = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 21a2 2 0 0 0 4 0"/></svg>'
    hs = ('<rect x="162" y="165" width="76" height="10" rx="5"/>'
          '<rect x="148" y="158" width="26" height="24" rx="8"/><rect x="226" y="158" width="26" height="24" rx="8"/>')
    keys = "".join(f'<circle cx="{x}" cy="{y}" r="2.4"/>' for y in (200, 207.5, 215) for x in (188, 200, 212))
    counter = f'''<svg class="ps-art" viewBox="0 0 400 360" aria-hidden="true">
<path d="M46 80H74L104 222H16zM326 80H354L384 222H296z" fill="#FFD86B" opacity=".07"/>
<path d="M60 0V64M340 0V64" stroke="#2E2E36" stroke-width="2"/>
<path d="M42 78a18 15 0 0 1 36 0zM322 78a18 15 0 0 1 36 0z" fill="#2A2A32" stroke="#45454F" stroke-width="1.5"/>
<circle cx="60" cy="80" r="4" fill="#FFE9B0"/><circle cx="340" cy="80" r="4" fill="#FFE9B0"/>
<rect x="128" y="64" width="144" height="80" rx="7" fill="#121216" stroke="#2C2C35" stroke-width="1.5"/>
<path d="M144 82H190" stroke="#FFC83D" stroke-width="5" stroke-linecap="round"/>
<path d="M144 100H210M144 114H200M144 128H216" stroke="#4E4E58" stroke-width="3.2" stroke-linecap="round"/>
<path d="M240 100H256M240 114H256M240 128H256" stroke="#85858F" stroke-width="3.2" stroke-linecap="round"/>
<rect x="26" y="232" width="348" height="128" fill="#111115" stroke="#24242C" stroke-width="1.5"/>
<path d="M142 236V360M258 236V360" stroke="#1C1C23" stroke-width="2"/>
<path d="M26 248H374" stroke="#FFC83D" stroke-width="2.4" opacity=".55"/>
<rect x="16" y="222" width="368" height="11" rx="4" fill="#2A2A33"/>
<rect x="68" y="216" width="46" height="6" rx="2" fill="#2E2E37"/>
<path d="M73 216a18 17 0 0 1 36 0z" fill="#2A2A32" stroke="#4A4A55" stroke-width="1.5"/>
<rect x="88" y="194" width="6" height="5" rx="1.5" fill="#4A4A55"/>
<path d="M80 210a11 10 0 0 1 7-7.5" stroke="#fff" stroke-opacity=".22" stroke-width="2" stroke-linecap="round"/>
<path d="M294 186l-3-16M301 184l-1-18M308 184l1-17M315 186l3-15" stroke="#FFD86B" stroke-width="4.5" stroke-linecap="round"/>
<path d="M288 184H322L316 222H294z" fill="#D9342B"/><path d="M291 196H319" stroke="#FFFDF6" stroke-opacity=".55" stroke-width="2"/>
<path d="M346 188v-6a8 8 0 0 1 16 0v6" stroke="#4A4A55" stroke-width="2"/>
<rect x="336" y="188" width="36" height="34" rx="2.5" fill="#1F1F26" stroke="#3A3A44" stroke-width="1.5"/><circle cx="354" cy="205" r="5.5" fill="#FFC83D"/>
<path d="M154 222L165 186Q167 179 174 179H226Q233 179 235 186L246 222z" fill="#1A1A20" stroke="#3E3E48" stroke-width="2" stroke-linejoin="round"/>
<rect x="184" y="186" width="32" height="7" rx="2" fill="#2A2A33"/><g fill="#3A3A44">{keys}</g>
<g class="ps-hs ps-hs-s" fill="#26262E" stroke="#4A4A55" stroke-width="2">{hs}</g>
<g class="ps-ringing"><rect x="184" y="186" width="32" height="7" rx="2" fill="#FFC83D"/>
<g class="ps-hs ps-hs-r" fill="#26262E" stroke="#4A4A55" stroke-width="2">{hs}</g>
<g stroke="#FFC83D" stroke-width="3.5" stroke-linecap="round"><path class="ps-arc" d="M139 156Q131 170 139 184M261 156Q269 170 261 184"/><path class="ps-arc ps-arc2" d="M128 150Q117 170 128 190M272 150Q283 170 272 190"/></g></g>
<circle class="ps-ripple" cx="200" cy="168" r="40" stroke="#FFD86B" stroke-width="2.5"/>
<path class="ps-burst" d="M200 106V92M220.7 111.2L227.2 98.8M179.3 111.2L172.8 98.8M236 124.8L247.5 116.7M164 124.8L152.5 116.7" stroke="#FFD86B" stroke-width="3.5" stroke-linecap="round"/>
</svg>'''
    timer = '<span class="ps-time"><span>' + "".join(f"<em>{x}</em>" for x in PS_TIMER) + "</span></span>"
    call = (f'<div class="ps-act ps-a2"><div class="ps-orb"><span class="ps-wv">{"<i></i>" * 7}</span></div>'
            f'<p class="ps-who">+57 310 •• •• 245 · {timer}</p>'
            f'<p class="ps-say ps-s1">{e(t["said"])}</p><p class="ps-say ps-s2">{e(t["answer"])}</p>'
            f'<p class="ps-ok">{check}{e(t["ok"])}</p></div>')
    rows = [("#1043", sc["chans"][0], sc["ps_times"][0], ", ".join(t["items"]), " ps-new"),
            ("#1042", sc["chans"][1], sc["ps_times"][1], sc["ps_rows"][0], ""),
            ("#1041", sc["chans"][2], sc["ps_times"][2], sc["ps_rows"][1], "")]
    rws = "".join(f'<div class="ps-row{cls}"><div><b>{n}</b><span>{e(ch)}</span><small>{e(tm)}</small></div><p>{e(it)}</p></div>'
                  for n, ch, tm, it, cls in rows)
    tk = "".join(f"<span>{e(x)}</span>" for x in t["items"])
    result = (f'<div class="ps-act ps-a3">'
              f'<div class="ps-scr"><div class="ps-bar"><b>{e(sc["orders_title"])}</b><span>{e(sc["ps_clock"])}</span></div>'
              f'<div class="ps-list"><div class="ps-rows">{rws}</div></div>'
              f'<div class="ps-toast"><i>{bell}</i><span><b>{e(t["new"])}</b><small>#1043 · {e(T(lang)["P"]["phone"]["name"])}</small></span></div></div>'
              f'<div class="ps-base"></div><div class="ps-box"><i class="ps-led"></i></div>'
              f'<div class="ps-paper"><div class="ps-tk"><b><span>ABLA</span><span>#1043</span></b><small>{e(t["via"])}</small>{tk}'
              f'<small class="ps-tf">{e(t["foot"])}</small></div></div>'
              f'<div class="ps-checks"><span class="ps-c1">{check}{e(t["checks"][0])}</span><span class="ps-c2">{check}{e(t["checks"][1])}</span></div></div>')
    wave = '<span class="wave"><i></i><i></i><i></i><i></i><i></i></span>'
    pill = (f'<div class="ps-pill"><span class="ps-p ps-p1"><i class="ps-dot"></i>{e(ring)}</span>'
            f'<span class="ps-p ps-p2"><i class="ps-dot ps-ai"></i>{e(picked)}{wave}</span>'
            f'<span class="ps-p ps-p3"><i class="ps-dot ps-go"></i>{e(sc["in_kitchen"])}</span></div>')
    return (f'<div class="pscene" role="img" aria-label="{e(T(lang)["UI"]["example"])}: {e(T(lang)["P"]["phone"]["name"])}">'
            f'<div class="ps-act ps-a1">{counter}</div>{call}{result}{pill}</div>')

FOOD_ICONS = {
    "burger": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11a8 6 0 0 1 16 0z"/><path d="M3 14.5h18"/><path d="M5 18h14a1.5 1.5 0 0 1 0 3H5a1.5 1.5 0 0 1 0-3z"/></svg>',
    "fries": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 11l1.5 10h7L17 11z"/><path d="M9 11V4M12 11V3M15 11V5"/></svg>',
    "drink": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 8h10l-1.2 13H8.2z"/><path d="M6 8h12M13 8l1.5-5H17"/></svg>',
    "hotdog": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.4 18.6a3 3 0 0 1 0-4.2l9-9a3 3 0 0 1 4.2 4.2l-9 9a3 3 0 0 1-4.2 0z"/><path d="M11.5 9.5l1.5 1.5M9 12l1.5 1.5"/></svg>',
}
WS_DELIVERY = 5000
WS_MINUTES = ["35", "25", "12"]

def web_i(lang):
    """Animated phone for the online store (same scene as on conveasy.be, see .wscene in site.css), in pesos."""
    sc = T(lang)["SC"]
    shop, tag, cats, items, btn = sc["web"]
    w = sc["wscene"]
    money = lambda n: cop(n, lang)
    sums = [0]
    for _, pr in items: sums.append(sums[-1] + pr)
    roll = lambda words, cls: f'<span class="ws-roll {cls}"><span>' + "".join(f"<em>{e(x)}</em>" for x in words) + "</span></span>"
    tap = '<u class="ws-tap"></u>'
    check = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
    bike = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18.5" cy="17.5" r="3.5"/><circle cx="5.5" cy="17.5" r="3.5"/><circle cx="15" cy="5" r="1"/><path d="M12 17.5V14l-3-3 4-3 2 3h2"/></svg>'
    c = "".join(f'<span{" class=on" if i == 0 else ""}>{e(x)}</span>' for i, x in enumerate(cats))
    it = "".join(f'<div class="ws-item ws-i{i}"><i>{FOOD_ICONS[ic]}</i><b>{e(n)}<small>{e(money(pr))}</small></b><span class="ws-add"><em>+</em>{check}{tap}</span></div>'
                 for i, ((n, pr), ic) in enumerate(zip(items, ["burger", "fries", "hotdog"]), 1))
    menu = (f'<div class="ws-view ws-menu"><div class="ws-head"><b>{e(shop)}</b><small>{e(tag)}</small></div><div class="ws-cats">{c}</div>{it}'
            f'<div class="ws-btn ws-order">{e(btn)} · {roll([money(x) for x in sums], "ws-tot")}{tap}</div></div>')
    typed = "".join(f'<i style="--i:{k}">{e(ch)}</i>' for k, ch in enumerate(w["addr"]))
    p1, p2, p3 = w["pay"]
    chips = f'<span class="ws-chip ws-sel">{e(p1)}{tap}</span><span class="ws-chip">{e(p2)}</span><span class="ws-chip">{e(p3)}</span>'
    checkout = (f'<div class="ws-view ws-check"><b class="ws-title">{e(w["checkout"])}</b>'
                f'<div class="ws-seg"><span>{e(w["modes"][0])}</span><span class="on">{e(w["modes"][1])}</span></div>'
                f'<div class="ws-lab">{e(w["addr_label"])}</div><div class="ws-field"><span class="ws-type">{typed}</span></div>'
                f'<div class="ws-fee">{check}{e(w["fee"].format(fee=money(WS_DELIVERY)))}</div>'
                f'<div class="ws-lab">{e(w["pay_label"])}</div><div class="ws-chips">{chips}</div>'
                f'<div class="ws-sums"><div><span>{e(w["sub"])}</span><span>{money(sums[-1])}</span></div>'
                f'<div><span>{e(w["ship"])}</span><span>{roll(["–", money(WS_DELIVERY)], "ws-tot2")}</span></div>'
                f'<div class="ws-sum"><span>{e(w["total"])}</span><b>{roll([money(sums[-1]), money(sums[-1] + WS_DELIVERY)], "ws-tot2")}</b></div></div>'
                f'<div class="ws-btn ws-place">{e(w["place"])}{tap}</div></div>')
    steps = "".join(f'<li class="ws-s{i}"><i></i>{e(x)}</li>' for i, x in enumerate(w["steps"], 1))
    route = "M12 21C24 21 22 8 36 8S52 20 64 20 76 9 88 8"
    route_map = ('<div class="ws-map"><svg viewBox="0 0 100 28" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
                 '<path class="ws-road" d="M-2 14H102M26-2V30M58-2V30M84-2V30M-2 3H102M-2 25H102"/>'
                 f'<path class="ws-route" d="{route}"/><path class="ws-ride" pathLength="100" d="{route}"/>'
                 '<circle class="ws-from" cx="12" cy="21" r="2.4"/><circle class="ws-to" cx="88" cy="8" r="2.4"/></svg></div>')
    done = (f'<div class="ws-view ws-done"><span class="ws-okc">{check}</span>'
            f'<div class="ws-thx"><b>{e(w["thanks"][0])}</b><small>{e(w["thanks"][1])}</small></div>'
            f'<div class="ws-eta"><small>{e(w["eta"])}</small><div class="ws-big"><b class="ws-count">{e(w["left"][0])}{roll(WS_MINUTES, "ws-min")}{e(w["left"][1])}</b>'
            f'<b class="ws-enjoy">{e(w["enjoy"])}</b></div><div class="ws-subs"><span class="ws-count">{e(w["around"])}</span><span class="ws-enjoy">{e(w["delivered"])}</span></div>'
            f'<span class="ws-drv">{bike}{e(w["driver"])}</span></div>'
            f'<ol class="ws-steps">{steps}</ol>{route_map}</div>')
    return f'<div class="phone wscene" role="img" aria-label="{e(T(lang)["UI"]["example"])}: {e(T(lang)["P"]["webshop"]["name"])}"><div class="ph-screen ws">{menu}{checkout}{done}</div></div>'

KS_LANGS = ["es", "en", "pt", "fr", "de"]   # the five languages the kiosk screen runs through
def kiosk_i(lang):
    """Animated kiosk (see .kscene in site.css): the screen switches language, a burger and fries go in, payment, ticket.
    The words show all five kiosk languages; --ks-i is the page language's place, where the scene rests without motion."""
    k = T(lang)["SC"]["kiosk"]
    def roll(words): return '<span class="ks-roll"><span>' + "".join(f"<em>{e(w)}</em>" for w in words) + "</span></span>"
    hello = "".join(f"<em>{e(w)}</em>" for w in ["Bienvenido", "Welcome", "Bem-vindo", "Bienvenue", "Willkommen"])
    chips = "".join(f"<i>{c}</i>" for c in ["ES", "EN", "PT", "FR", "DE"])
    rows = [("burger", ["Hamburguesa", "Burger", "Hambúrguer", "Burger", "Burger"], 22000),
            ("fries", ["Papas", "Fries", "Batata frita", "Frites", "Pommes"], 8000),
            ("drink", ["Gaseosa", "Soda", "Refrigerante", "Soda", "Limo"], 4500)]
    items = "".join(f'<div class="ks-item ks-{kk}">{FOOD_ICONS[kk]}<span class="ks-n"><b>{roll(w)}</b><small>{e(cop(pr, "es"))}</small></span><u>+</u></div>' for kk, w, pr in rows)
    return f'''<div class="kscene" style="--ks-i: {KS_LANGS.index(lang)}" role="img" aria-label="{e(T(lang)["UI"]["example"])}: {e(k)}">
<div class="ks-kiosk"><div class="ks-frame"><div class="ks-screen">
<div class="ks-view ks-lang"><span class="ks-hello"><span>{hello}</span></span><div class="ks-chips">{chips}</div></div>
<div class="ks-view ks-menu"><div class="ks-top">{roll(["Menú", "Menu", "Cardápio", "Carte", "Speisekarte"])}<span class="ks-cart"><span><em>0</em><em>1</em><em>2</em></span></span></div>{items}<div class="ks-go">{roll(["Pedir", "Order", "Pedir", "Commander", "Bestellen"])}</div></div>
<div class="ks-view ks-pay"><b>{e(cop(30000, "es"))}</b><span class="ks-card"></span><span class="ks-ok"></span></div>
</div></div><div class="ks-slot"><span class="ks-ticket">#47</span></div><div class="ks-stand"></div><div class="ks-base"></div></div>
<svg class="ks-man" viewBox="0 0 100 180" aria-hidden="true"><circle cx="52" cy="22" r="13"/><path d="M52 35v68M52 103l-15 73M52 103l15 73M52 52l15 44"/><g class="ks-arm"><path d="M52 52v46"/><circle cx="52" cy="99" r="3.2"/></g></svg>
<div class="ks-floor"></div></div>'''

def types_i(lang):
    title, sub, kinds, yours = T(lang)["TYPES"]
    chips = "".join(f'<span style="--i:{i}">{e(k)}</span>' for i, k in enumerate(kinds))
    chips += f'<span class="ty-you" style="--i:{len(kinds)}">+ {e(yours)}</span>'
    return (f'<div class="panel types" role="img" aria-label="{e(T(lang)["UI"]["example"])}: {e(title)}">'
            f'<div class="p-title">{e(title)}<span>{e(sub)}</span></div><div class="ty-chips">{chips}</div></div>')

def framed(lang, inner):
    return f'<div>{inner}<p class="mock-label">{e(T(lang)["UI"]["example"])}</p></div>'

def sector_chat(lang, sid):
    d = T(lang)["S"][sid]
    cust, ai, done = d["chat"]
    sc = T(lang)["SC"]
    return {"msgs": [cust, ai, sc["btns"], sc["btns"][0], done], "times": sc["order"]["times"]}

def hero_stage(lang, scene, ticket_html=None, pill=True):
    """The WhatsApp phone as the hero: the order chat, the kitchen ticket that prints when the order is confirmed,
    and a small pill with the number of chats the AI is answering right now."""
    sc = T(lang)["SC"]
    pl = (f'<div class="sw-pill" aria-hidden="true"><i></i><b>52</b><span>{e(sc["inbox"]["count_label"])}</span></div>' if pill else "")
    tk = f'<div class="sw-ticket" aria-hidden="true">{ticket_html}</div>' if ticket_html else ""
    return (f'<div class="stage-wa">{wa_chat(lang, scene, "order", big=True)}{tk}{pl}</div>'
            f'<p class="mock-label">{e(T(lang)["UI"]["example"])}</p>')

def mock_for(lang, pid):
    sc = T(lang)["SC"]
    if pid == "whatsapp": return hero_stage(lang, sc["order"], home_ticket(lang))
    if pid == "phone": return framed(lang, phone_scene_i(lang))
    if pid == "webshop": return framed(lang, web_i(lang))
    if pid == "kiosk": return framed(lang, kiosk_i(lang))
    if pid == "todos": return framed(lang, types_i(lang))
    if pid in SECTORS:
        d = T(lang)["S"][pid]
        return hero_stage(lang, sector_chat(lang, pid), ticket_i(lang, d["ticket"], *sc["ticket_meta"]), pill=False)
    return ""

# ---------------- Sections ----------------
def crumbs_html(lang, prefix, trail):
    lis = "".join(f'<li><a href="{prefix + path_of(lang, p)}">{e(n)}</a></li>' if p else f'<li aria-current="page">{e(n)}</li>' for n, p in trail)
    return f'<nav aria-label="{e(T(lang)["UI"]["crumbs_label"])}"><ol class="crumbs">{lis}</ol></nav>'

def faq_band(lang, faqs, page):
    u = T(lang)["UI"]
    items = "".join(f'<details><summary>{e(fill(q, lang))}</summary><p>{ph(fill(a, lang), lang, page)}</p></details>' for q, a in faqs)
    return f'''<section class="band" id="faq"><div class="wrap faq-wrap"><div class="section-head"><span class="eyebrow">{e(u["faq_eyebrow"])}</span><h2>{e(u["faq_title"])}</h2></div><div class="faq">{items}</div></div></section>'''

def cta_band(lang, prefix):
    u = T(lang)["UI"]
    return f'''<section class="band dark cta"><div class="wrap"><h2>{e(u["cta_title"])}</h2><p>{e(u["cta_text"])}</p>
<div class="btn-row"><a class="btn btn-primary" href="{prefix + path_of(lang, "contact")}">{e(u["demo"])} <span class="arr" aria-hidden="true">→</span></a><a class="btn btn-ghost" href="{wa_href(lang, prefix)}" rel="noopener">{e(u["wa"])}</a></div></div></section>'''

def how_band(lang):
    u = T(lang)["UI"]
    steps = "".join(f'<li><span class="step-n">{e(u["step"])} {i}</span><h3>{e(t)}</h3><p class="note">{e(d)}</p></li>' for i, (t, d) in enumerate(u["steps"], 1))
    return (f'<section class="band"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(u["how_eyebrow"])}</span><h2>{e(u["how_title"])}</h2></div>'
            f'<ol class="steps">{steps}</ol><p class="need"><span class="need-ic" aria-hidden="true"></span>{e(u["need"])}</p></div></section>')

def scenes_band(lang, eyebrow, title, text, dark=False):
    """WhatsApp in action: four small phones, each with a caption."""
    sc = T(lang)["SC"]
    caps = T(lang)["HOME"]["scenes"]
    figs = [inbox(lang), wa_chat(lang, sc["menu"], "qa"), wa_chat(lang, sc["resv"], "qa"), wa_chat(lang, sc["tour"], "order", shop=sc["shop"])]
    cards = "".join(f'<figure class="sc-card">{f}<figcaption><h3>{e(fill(t, lang))}</h3><p>{e(fill(x, lang))}</p></figcaption></figure>' for f, (t, x) in zip(figs, caps))
    cls = "band dark" if dark else "band"
    return (f'<section class="{cls} wa-scenes" id="whatsapp"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(eyebrow)}</span><h2>{e(title)}</h2><p>{e(text)}</p></div>'
            f'<div class="sc-row">{cards}</div><p class="mock-label">{e(T(lang)["UI"]["example"])}</p></div></section>')

def flow_band(lang):
    eb, title, steps = T(lang)["FLOW"]
    sc = T(lang)["SC"]
    screens = [wa_chat(lang, sc["order"], "order"), wa_chat(lang, sc["menu"], "qa"), home_ticket(lang), inbox(lang)]
    stage = "".join(f'<div class="fs" data-s="{i}">{s}</div>' for i, s in enumerate(screens))
    lis = "".join(f'<li data-s="{i}"{" class=on" if i == 0 else ""}><span class="fs-n">0{i+1} / 04</span><h3>{e(t)}</h3><p>{e(x)}</p><div class="fs-inline" aria-hidden="true">{screens[i]}</div></li>' for i, (t, x) in enumerate(steps))
    return (f'<section class="band dark flow"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(eb)}</span><h2>{e(title)}</h2></div>'
            f'<div class="flow-grid"><ol class="flow-steps">{lis}</ol><div class="flow-stage" data-step="0" aria-hidden="true">{stage}</div></div></div></section>')

def product_cards(lang, prefix, exclude=None, pos=False):
    """Product cards. With pos=True (the home page bento) the WhatsApp card also gets two small chat bubbles and the POS card is added."""
    t, u = T(lang), T(lang)["UI"]
    out = []
    for p in PRODUCTS:
        if p == exclude: continue
        d = t["P"][p]
        tag = f'<span class="tag">{e(d["badge"])}</span>' if d.get("badge") else ""
        mini = ""
        if pos and p == "whatsapp":
            m = t["SC"]["order"]["msgs"]
            mini = (f'<div class="card-chat" aria-hidden="true"><span class="cc-out">{e(m[0])}</span>'
                    f'<span class="cc-in">{e(m[4])}</span></div>')
        out.append(f'<a class="card" href="{prefix + path_of(lang, p)}">{tag}<h3>{e(d["name"])}</h3><p>{e(fill(d["card"], lang))}</p><span class="more">{e(u["more"])} →</span>{mini}</a>')
    if pos:
        pt, px = t["HOME"]["pos_card"]
        out.append(f'<a class="card" href="{prefix + path_of(lang, "contact")}"><h3>{e(pt)}</h3><p>{e(px)}</p><span class="more">{e(u["ask"])} →</span></a>')
    return "".join(out)

def hero(lang, prefix, h1, lead, mock, page, badge=None, facts=None, extra="", cls=""):
    u = T(lang)["UI"]
    b = f'<span class="badge"><i aria-hidden="true"></i>{e(badge)}</span>' if badge else ""
    f = ('<ul class="stats">' + "".join(f"<li><b>{e(x)}</b></li>" for x in facts) + "</ul>") if facts else ""
    st = f'<div class="stage">{mock}</div>' if mock else ""
    return f'''<section class="hero{cls}"><div class="hero-bg" aria-hidden="true"></div><div class="wrap"><div class="hero-copy">{extra}{b}<h1>{rich(h1, lang, page)}</h1><p class="lead">{ph(fill(lead, lang), lang, page)}</p>
<div class="btn-row"><a class="btn btn-primary" href="{prefix + path_of(lang, "contact")}">{e(u["demo"])} <span class="arr" aria-hidden="true">→</span></a><a class="btn btn-ghost" href="{wa_href(lang, prefix)}" rel="noopener">{e(u["wa"])}</a></div></div>{st}{f}</div></section>'''

def price_card(lang, name, amount, per, sub, feats, page, pop=False, pop_label="", note="", cls=""):
    badge = f'<span class="chip">{e(pop_label)}</span>' if pop else ""
    amt = f'{e(cop(amount, lang))}<small>{e(per)}</small>' if isinstance(amount, int) else f'<span class="amount-q">{e(amount)}</span>'
    lis = "".join(f"<li>{e(fill(x, lang))}</li>" for x in feats)
    n = f'<p class="note">{ph(fill(note, lang), lang, page)}</p>' if note else ""
    sb = f'<p class="sub">{e(fill(sub, lang))}</p>' if sub else ""
    return f'<div class="price{" pop" if pop else ""}{cls}"><h3>{e(name)}{badge}</h3><div class="amount">{amt}</div>{sb}<ul>{lis}</ul>{n}</div>'

def wa_price_cards(lang, page):
    t, u, pr = T(lang), T(lang)["UI"], T(lang)["PRICING"]
    main = price_card(lang, t["P"]["whatsapp"]["name"], PRICE["wa"], u["per_month"], pr["wa_sub"], pr["wa_feats"], page, True, u["main"], pr["setup_note"])
    adds = "".join(price_card(lang, n, PRICE[k], u["per_month"], s, f, page, cls=" addon") for k, n, s, f in pr["addons"])
    return main + adds

def quote_card(lang, pid, page):
    t, u, pr = T(lang), T(lang)["UI"], T(lang)["PRICING"]
    return price_card(lang, t["P"][pid]["name"], u["quote"], "", u["quote_sub"], pr["other_feats"][pid], page)

def product_price_band(lang, pid, prefix, page):
    u = T(lang)["UI"]
    body = wa_price_cards(lang, page) if pid == "whatsapp" else quote_card(lang, pid, page)
    return f'''<section class="band"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(u["pricing"])}</span><h2>{e(u["price_title"])}</h2></div><div class="price-grid">{body}</div>
<p class="note" style="margin-top:16px"><a href="{prefix + path_of(lang, "pricing")}">{e(u["see_prices"])} →</a></p></div></section>'''

# ---------------- Pages ----------------
def page_home(lang, prefix):
    t = T(lang); d, u, sc = t["HOME"], t["UI"], t["SC"]
    pg = f"{lang}/home"
    sec_cards = "".join(f'<a class="card" href="{prefix + path_of(lang, s)}"><h3>{e(t["S"][s]["name"])}</h3><p>{e(t["S"][s].get("card", t["S"][s]["pains"][0][1]))}</p><span class="more">{e(u["more"])} →</span></a>' for s in SECTORS)
    body = hero(lang, prefix, d["h1"], d["lead"], hero_stage(lang, sc["order"], home_ticket(lang)), pg, badge=d["badge"], facts=d["facts"], cls=" hero-wa")
    body += scenes_band(lang, d["wa_eyebrow"], d["wa_title"], d["wa_text"])
    body += flow_band(lang)
    body += f'''<section class="band" id="productos"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(d["products_eyebrow"])}</span><h2>{e(d["products_title"])}</h2><p>{e(d["products_text"])}</p></div>
<div class="bento bento-abla">{product_cards(lang, prefix, pos=True)}</div></div></section>
<section class="band"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(d["sectors_eyebrow"])}</span><h2>{e(d["sectors_title"])}</h2><p>{e(d["sectors_text"])}</p></div><div class="grid">{sec_cards}</div></div></section>
{how_band(lang)}
<section class="band"><div class="wrap grid-3" style="align-items:start">
<div class="section-head" style="margin:0;grid-column:span 2;max-width:none"><span class="eyebrow">{e(d["story_eyebrow"])}</span><h2>{e(d["story_title"])}</h2><p class="lead">{e(d["story_text"])}</p><p><a href="{prefix + path_of(lang, "about")}">{e(d["story_link"])} →</a></p></div>
<div class="card"><span class="eyebrow" style="margin:0">{e(d["price_eyebrow"])}</span><h3>{e(fill(d["price_title"], lang))}</h3><p>{e(fill(d["price_text"], lang))}</p><a class="more" href="{prefix + path_of(lang, "pricing")}">{e(u["see_prices"])} →</a></div>
</div></section>'''
    body += faq_band(lang, d["faq"], pg) + cta_band(lang, prefix)
    return body, d["faq"], []

def page_product(lang, pid, prefix):
    t = T(lang); d, u = t["P"][pid], t["UI"]
    pg = f"{lang}/{pid}"
    trail = [(u["home"], "home"), (d["name"], None)]
    feats = "".join(f'<div class="feature"><h3>{e(fill(a, lang))}</h3><p>{ph(fill(x, lang), lang, pg)}</p></div>' for a, x in d["features"])
    body = hero(lang, prefix, d["h1"], d["lead"], mock_for(lang, pid), pg, badge=d.get("badge"), extra=crumbs_html(lang, prefix, trail),
                cls=" hero-wa" if pid == "whatsapp" else "")
    if pid == "whatsapp":
        h = t["HOME"]
        body += scenes_band(lang, h["wa_eyebrow"], d["scenes_title"], d["scenes_text"], dark=True)
    body += f'<section class="band"><div class="wrap"><div class="grid">{feats}</div></div></section>'
    if pid == "whatsapp":
        body += flow_band(lang)
    body += product_price_band(lang, pid, prefix, pg)
    body += how_band(lang)
    body += f'''<section class="band"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(u["products"])}</span><h2>{e(u["other_products"])}</h2><p>{e(u["all_in_one"])}</p></div><div class="grid">{product_cards(lang, prefix, exclude=pid)}</div></div></section>'''
    body += faq_band(lang, d["faq"], pg) + cta_band(lang, prefix)
    crumbs = [(u["home"], canonical(lang, "home")), (d["name"], canonical(lang, pid))]
    return body, d["faq"], crumbs

def page_sector(lang, sid, prefix):
    t = T(lang); d, u = t["S"][sid], t["UI"]
    pg = f"{lang}/{sid}"
    trail = [(u["home"], "home"), (d["name"], None)]
    pains = "".join(f'<div class="feature"><h3>{e(a)}</h3><p>{e(fill(x, lang))}</p></div>' for a, x in d["pains"])
    body = hero(lang, prefix, d["h1"], d["lead"], mock_for(lang, sid), pg, extra=crumbs_html(lang, prefix, trail), cls=" hero-wa" if sid != "todos" else "")
    body += f'<section class="band"><div class="wrap"><div class="grid">{pains}</div></div></section>'
    body += f'''<section class="band"><div class="wrap"><div class="section-head"><span class="eyebrow">{e(u["products"])}</span><h2>{e(t["HOME"]["products_title"])}</h2><p>{e(t["HOME"]["products_text"])}</p></div><div class="grid">{product_cards(lang, prefix)}</div></div></section>'''
    body += how_band(lang) + faq_band(lang, d["faq"], pg) + cta_band(lang, prefix)
    crumbs = [(u["home"], canonical(lang, "home")), (d["name"], canonical(lang, sid))]
    return body, d["faq"], crumbs

def page_pricing(lang, prefix):
    t = T(lang); d, u = t["PRICING"], t["UI"]
    pg = f"{lang}/pricing"
    trail = [(u["home"], "home"), (u["pricing"], None)]
    others = "".join(quote_card(lang, p, pg) for p in PRODUCTS if p != "whatsapp")
    pt, px = t["HOME"]["pos_card"]
    others += price_card(lang, pt, u["quote"], "", u["quote_sub"], [px], pg)
    body = f'''<section class="hero"><div class="wrap" style="grid-template-columns:minmax(0,1fr)"><div class="hero-copy">{crumbs_html(lang, prefix, trail)}<h1>{e(d["h1"])}</h1><p class="lead">{e(fill(d["lead"], lang))}</p></div></div></section>
<section class="band" style="padding-top:0"><div class="wrap">
<div class="price-group"><h2>{e(d["wa_h"])}</h2><p class="note">{e(fill(d["wa_note"], lang))}</p><div class="price-grid price-wa">{wa_price_cards(lang, pg)}</div></div>
<div class="price-group"><h2>{e(d["other_h"])}</h2><p class="note">{e(d["other_note"])}</p><div class="price-grid">{others}</div></div>
<div class="card" style="max-width:820px"><h3>{e(d["need_h"])}</h3><p>{e(d["need_text"])}</p><p>{e(fill(d["currency"], lang))}</p><p><a class="more" href="{prefix + path_of(lang, "contact")}">{e(u["demo"])} →</a></p></div>
</div></section>'''
    body += faq_band(lang, d["faq"], pg) + cta_band(lang, prefix)
    return body, d["faq"], [(u["home"], canonical(lang, "home")), (u["pricing"], canonical(lang, "pricing"))]

def page_about(lang, prefix):
    t = T(lang); d, u = t["ABOUT"], t["UI"]
    pg = f"{lang}/about"
    trail = [(u["home"], "home"), (u["about"], None)]
    blocks = "".join(f'<div class="card"><h3>{e(a)}</h3><p>{ph(fill(x, lang), lang, pg)}</p></div>' for a, x in d["blocks"])
    body = f'''<section class="hero"><div class="wrap" style="grid-template-columns:minmax(0,1fr)"><div class="hero-copy">{crumbs_html(lang, prefix, trail)}<h1>{e(d["h1"])}</h1><p class="lead">{e(d["lead"])}</p></div></div></section>
<section class="band" style="padding-top:0"><div class="wrap"><div class="grid">{blocks}</div></div></section>'''
    body += cta_band(lang, prefix)
    return body, [], [(u["home"], canonical(lang, "home")), (u["about"], canonical(lang, "about"))]

def page_contact(lang, prefix):
    t = T(lang); d, u = t["CONTACT"], t["UI"]
    pg = f"{lang}/contact"
    trail = [(u["home"], "home"), (u["contact"], None)]
    checks = "".join(f'<label><input type="checkbox" id="int-{p}" name="interest" value="{p}"{" checked" if p == "whatsapp" else ""}> {e(t["P"][p]["name"])}</label>' for p in PRODUCTS)
    wa_btn = (f'<div class="btn-row"><a class="btn btn-primary" href="https://wa.me/{WA_NUMBER}" rel="noopener">{e(d["open_wa"])}</a></div><p class="call-number">{e(WA_DISPLAY)}</p>'
              if WA_NUMBER else f'<p>{ph("{{PH:" + u["ph_wa"] + "}}", lang, pg)}</p>')
    email = f'<p><a href="mailto:{EMAIL}">{e(EMAIL)}</a></p>' if EMAIL else f'<p>{ph("{{PH:" + u["ph_email"] + "}}", lang, pg)}</p>'
    body = f'''<section class="hero"><div class="wrap" style="grid-template-columns:minmax(0,1fr)"><div class="hero-copy">{crumbs_html(lang, prefix, trail)}<h1>{e(d["h1"])}</h1><p class="lead">{e(d["lead"])}</p></div></div></section>
<section class="band" style="padding-top:0"><div class="wrap contact-grid">
<div class="wa-box card" id="whatsapp"><h2 style="font-size:1.4rem">{e(d["wa_h"])}</h2><p>{e(d["wa_text"])}</p>{wa_btn}
<h3 style="margin-top:12px">{e(d["visit_h"])}</h3><p>{e(d["visit_text"])}</p>
<h3 style="margin-top:12px">{e(d["email_h"])}</h3>{email}</div>
<form class="lead-form" novalidate data-wa="{WA_NUMBER}" data-to="{EMAIL}" data-subject="{e(d["f_subject"])}">
<div class="two"><div class="field"><label for="f-name">{e(d["f_name"])}</label><input id="f-name" name="name" autocomplete="name" required></div>
<div class="field"><label for="f-rest">{e(d["f_rest"])}</label><input id="f-rest" name="restaurant" autocomplete="organization" required></div></div>
<div class="two"><div class="field"><label for="f-city">{e(d["f_city"])}</label><input id="f-city" name="city" autocomplete="address-level2"></div>
<div class="field"><label for="f-phone">{e(d["f_phone"])}</label><input id="f-phone" name="phone" type="tel" autocomplete="tel" required></div></div>
<div class="field"><label for="f-email">{e(d["f_email"])}</label><input id="f-email" name="email" type="email" autocomplete="email"></div>
<fieldset><legend>{e(d["f_int"])}</legend><div class="checks">{checks}</div></fieldset>
<div class="field"><label for="f-msg">{e(d["f_msg"])}</label><textarea id="f-msg" name="message" rows="3"></textarea></div>
<button class="btn btn-primary" type="submit">{e(d["f_send"])}</button>
<p class="form-msg" hidden>{ph(d["f_note"] if (WA_NUMBER or EMAIL) else d["f_note_pending"], lang, pg)}</p>
</form></div></section>'''
    return body, [], [(u["home"], canonical(lang, "home")), (u["contact"], canonical(lang, "contact"))]

def page_legal(lang, prefix):
    t = T(lang); d, u = t["LEGAL"], t["UI"]
    pg = f"{lang}/legal"
    toc = "".join(f'<li><a href="#{doc["id"]}">{e(doc["title"])}</a></li>' for doc in d["docs"])
    docs = ""
    for doc in d["docs"]:
        secs = ""
        for head_, parts in doc["sections"]:
            inner = "".join(f"<p>{ph(fill(x, lang), lang, pg)}</p>" if isinstance(x, str) else "<ul>" + "".join(f"<li>{ph(fill(i, lang), lang, pg)}</li>" for i in x) + "</ul>" for x in parts)
            secs += f'<h3 style="font-size:1.05rem;margin-top:1.4em">{e(head_)}</h3>{inner}'
        docs += f'<h2 id="{doc["id"]}" style="font-size:1.5rem;margin-top:2em;scroll-margin-top:96px">{e(doc["title"])}</h2><p style="opacity:.7">{e(d["updated"])}</p><p>{ph(doc["intro"], lang, pg)}</p>{secs}'
    body = f"""<section class="hero"><div class="wrap" style="grid-template-columns:minmax(0,1fr)"><div class="hero-copy"><h1>{e(d["h1"])}</h1></div></div></section>
<section class="band" style="padding-top:0"><div class="wrap"><div class="prose"><h2 style="font-size:1.3rem">{e(d["company_h"])}</h2><p>{ph(d["company"], lang, pg)}</p><ul>{toc}</ul>{docs}</div></div></section>"""
    return body, [], []

def render(lang, pid, prefix, preview):
    if pid == "home": body, faqs, crumbs = page_home(lang, prefix)
    elif pid in PRODUCTS: body, faqs, crumbs = page_product(lang, pid, prefix)
    elif pid in SECTORS: body, faqs, crumbs = page_sector(lang, pid, prefix)
    else: body, faqs, crumbs = {"pricing": page_pricing, "about": page_about, "contact": page_contact, "legal": page_legal}[pid](lang, prefix)
    bar = f'<div class="preview-bar"><div class="wrap">{e(T(lang)["UI"]["preview"])}</div></div>' if preview else ""
    inner = f'{bar}{header(lang, pid, prefix)}<main>{body}</main>{footer(lang, prefix, f"{lang}/{pid}")}<script src="{prefix}assets/site.js{ASSET_Q["js"]}"></script>'
    hd = head(lang, pid, prefix, faqs, crumbs)
    return f'<!doctype html>\n<html lang="{T(lang)["HTML_LANG"]}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n{hd}\n</head>\n<body>\n{inner}\n</body>\n</html>\n'

def not_found(prefix):
    """404 page for GitHub Pages, in Spanish with links to every language's home."""
    t = T(DEFAULT)
    title, text = t["NOT_FOUND"]
    links = "".join(f'<a class="btn btn-ghost" href="{prefix}{l}/" hreflang="{l}">{e(T(l)["LANG_NAME"])}</a>' for l in LANGS)
    body = f'<section class="hero"><div class="wrap" style="grid-template-columns:minmax(0,1fr)"><div class="hero-copy"><h1>{e(title)}</h1><p class="lead">{e(text)}</p><div class="btn-row">{links}</div></div></div></section>'
    inner = f'{header(DEFAULT, "home", prefix)}<main>{body}</main>{footer(DEFAULT, prefix, "404")}<script src="{prefix}assets/site.js{ASSET_Q["js"]}"></script>'
    return (f'<!doctype html>\n<html lang="{t["HTML_LANG"]}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{e(title)} | Abla IA</title><meta name="robots" content="noindex">'
            f'<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{FONTS}">'
            f'<link rel="stylesheet" href="{prefix}assets/site.css{ASSET_Q["css"]}"><link rel="stylesheet" href="{prefix}assets/scenes.css{ASSET_Q["scenes"]}">\n</head>\n<body>\n{inner}\n</body>\n</html>\n')

def sitemap():
    urls = []
    for pid in PAGES:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{canonical(l, pid)}"/>' for l in LANGS)
        for l in LANGS:
            urls.append(f"<url><loc>{canonical(l, pid)}</loc>{alts}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(urls) + "\n</urlset>\n")

ROBOTS = f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"

def llms():
    t = T("en")
    lines = ["# Abla IA", "", "> " + plain(fill(t["HOME"]["desc"], "en")), "",
             "Abla IA is a WhatsApp AI for restaurants in Colombia: it answers customers on WhatsApp 24/7, takes the full order, "
             "has the customer confirm it and prints the ticket in the kitchen. It talks with 50+ customers at the same time. "
             "Abla also offers a phone AI, an online store with QR ordering, a self-order kiosk and a POS.",
             "", "## Prices (Colombian pesos)",
             f"- WhatsApp AI: {cop(PRICE['wa'], 'en')} a month, plus a one-time installation of {cop(PRICE['setup'], 'en')}",
             f"- Reservations by WhatsApp: {cop(PRICE['resv_addon'], 'en')} a month on top, or reservations only {cop(PRICE['resv_only'], 'en')} a month",
             f"- Extra language: {cop(PRICE['lang'], 'en')} a month per language (Spanish included, 60+ languages available)",
             "- Phone AI, online store, kiosk and POS: quote per restaurant",
             "- No commission per order. Restaurants need a laptop and a ticket printer.", "", "## Pages (English)"]
    for pid in PAGES:
        lines.append(f"- [{name_of('en', pid)}]({canonical('en', pid)})")
    lines += ["", "## Languages", "Spanish (" + SITE + "/es/), Portuguese (" + SITE + "/pt/), English (" + SITE + "/en/), French (" + SITE + "/fr/)."]
    return "\n".join(lines) + "\n"

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def build(outdir, preview):
    if os.path.isdir(outdir): shutil.rmtree(outdir)
    os.makedirs(os.path.join(outdir, "assets"))
    for name in ("site.css", "site.js", "favicon.svg", "apple-touch-icon.png"):
        shutil.copy(os.path.join(HERE, name), os.path.join(outdir, "assets", name))
    write(os.path.join(outdir, "assets", "scenes.css"), scenes_css())
    ASSET_Q.update(css="" if preview else "?v=" + asset_fingerprint(os.path.join(HERE, "site.css")),
                   js="" if preview else "?v=" + asset_fingerprint(os.path.join(HERE, "site.js")),
                   scenes="" if preview else "?v=" + asset_fingerprint(os.path.join(outdir, "assets", "scenes.css")))
    for l in LANGS:
        for pid in PAGES:
            write(os.path.join(outdir, path_of(l, pid)), render(l, pid, "../", preview))
    write(os.path.join(outdir, "index.html"), render(DEFAULT, "home", "", preview))
    write(os.path.join(outdir, "404.html"), not_found("/" if not preview else ""))
    write(os.path.join(outdir, "sitemap.xml"), sitemap())
    write(os.path.join(outdir, "robots.txt"), ROBOTS)
    write(os.path.join(outdir, "llms.txt"), llms())

def check_structure():
    """Every language must have the same keys as Spanish, so a missing translation fails the build instead of the page."""
    def walk(a, b, path):
        if isinstance(a, dict):
            assert isinstance(b, dict), path
            for k in a:
                assert k in b, f"missing {path}/{k}"
                walk(a[k], b[k], f"{path}/{k}")
        elif isinstance(a, (list, tuple)) and a and isinstance(a[0], (list, tuple, dict)):
            assert len(a) == len(b), f"length {path}: {len(a)} vs {len(b)}"
            for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f"{path}[{i}]")
    for l in LANGS:
        if l != DEFAULT: walk(D[DEFAULT], D[l], l)

if __name__ == "__main__":
    check_structure()
    build(os.path.join(ROOT, "docs"), False)
    write(os.path.join(ROOT, "docs", ".nojekyll"), "")
    if CUSTOM_DOMAIN: write(os.path.join(ROOT, "docs", "CNAME"), CUSTOM_DOMAIN + "\n")
    PLACEHOLDERS.clear()
    build(os.path.join(ROOT, "preview"), True)
    es = sorted({t for (l, t) in PLACEHOLDERS if l == DEFAULT})
    write(os.path.join(ROOT, "PLACEHOLDERS.txt"), ("\n".join(es) + "\n") if es else "Nada por completar.\n")
    print("pages per lang:", len(PAGES), "| langs:", len(LANGS), "| placeholders (es):", len(es))
    for x in es: print(" -", x)
