#!/usr/bin/env python3
"""Link preview images (og:image, 1200x630) for abla.co, one per language, into src/og/og-<lang>.jpg.
The build copies them to assets/og/ and every page points to the image of its language.
Run again after changing the home page headline, the facts or the kitchen ticket: python3 tools/og_images.py
Needs Playwright for Python and Google Chrome (or Chromium). The fonts are in tools/fonts (Plus Jakarta Sans, SIL Open Font License)."""
import asyncio, html, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import importlib.util
spec = importlib.util.spec_from_file_location("site_build", os.path.join(ROOT, "src", "build.py"))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

FONT_DIR = os.path.join(HERE, "fonts")
def faces():
    out = []
    for w in (500, 700, 800):
        out.append(f"@font-face{{font-family:F;font-weight:{w};src:url('file://{FONT_DIR}/plus-jakarta-sans-latin-ext-{w}-normal.woff2') format('woff2');"
                   "unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}")
        out.append(f"@font-face{{font-family:F;font-weight:{w};src:url('file://{FONT_DIR}/plus-jakarta-sans-latin-{w}-normal.woff2') format('woff2');"
                   "unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}")
    return "".join(out)

def page(lang):
    e = lambda s: html.escape(s, quote=True)
    t = b.T(lang); d, sc = t["HOME"], t["SC"]
    h1 = e(d["h1"]).replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")
    chips = "".join(f"<span>{e(x)}</span>" for x in d["facts"])
    msg = e(sc["order"]["msgs"][0])
    lis = "".join(f'<li class="sub">{e(x)}</li>' if not q else f"<li><b>{e(q)}</b>{e(x)}</li>" for q, x in sc["ticket_items"])
    via, when = sc["ticket_meta"]
    return f"""<!doctype html><html lang="{t['HTML_LANG']}"><head><meta charset="utf-8"><style>{faces()}
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;background:#0F0B16;color:#F5F1FB;font-family:F,system-ui,sans-serif;overflow:hidden;position:relative}}
.glow{{position:absolute;right:-180px;bottom:-260px;width:900px;height:900px;border-radius:50%;background:radial-gradient(closest-side,rgb(129 74 200/.62),rgb(129 74 200/.16) 55%,transparent 75%)}}
.ring{{position:absolute;right:120px;top:40px;width:520px;height:520px;border-radius:50%;border:2px solid rgb(201 162 255/.22)}}
.wrap{{position:absolute;inset:64px 72px;display:grid;grid-template-rows:auto 1fr auto;gap:24px;width:680px}}
.logo{{display:flex;align-items:center;gap:12px;font-weight:800;font-size:42px;letter-spacing:-.03em}}
.logo svg{{width:50px;height:50px}} .logo .lm-b{{fill:#A774F0}} .logo .lm-d{{fill:#0F0B16}}
.logo sup{{font-size:17px;font-weight:800;background:#814AC8;color:#FFFFFF;border-radius:6px;padding:3px 7px;margin-left:-2px;align-self:flex-start;margin-top:4px}}
h1{{align-self:center;font-weight:800;font-size:62px;line-height:1.05;letter-spacing:-.035em;text-wrap:balance}}
h1 em{{font-style:normal;color:#25D366}}
.chips{{display:flex;flex-wrap:wrap;gap:10px}}
.chips span{{border:1px solid rgb(255 255 255/.18);background:#1B1526;border-radius:999px;padding:9px 16px;font-weight:500;font-size:21px}}
.bubble{{position:absolute;right:86px;top:84px;width:330px;background:#D9FDD3;color:#111b21;border-radius:16px 4px 16px 16px;padding:16px 18px;font-size:21px;font-weight:500;line-height:1.3;
  box-shadow:0 20px 50px rgb(0 0 0/.5);transform:rotate(-2deg)}}
.ticket{{position:absolute;right:70px;top:250px;width:330px;background:#FCFAFF;color:#1E1D19;border-radius:6px;padding:20px 24px 16px;transform:rotate(4deg);box-shadow:0 30px 80px rgb(0 0 0/.6)}}
.ticket::after{{content:"";position:absolute;left:0;right:0;bottom:-10px;height:12px;background:linear-gradient(-45deg,transparent 6px,#FCFAFF 0) 0 0/12px 12px repeat-x,linear-gradient(45deg,transparent 6px,#FCFAFF 0) 0 0/12px 12px repeat-x}}
.t-head{{display:flex;justify-content:space-between;font-weight:800;font-size:22px;letter-spacing:.06em;border-bottom:2px dashed #DDD5EA;padding-bottom:10px}}
.t-meta{{display:grid;gap:2px;font-size:16px;color:#5b5a52;padding:10px 0;border-bottom:2px dashed #DDD5EA}}
ul{{list-style:none;padding:10px 0 4px;display:grid;gap:7px;font-size:19px;font-weight:700}}
li b{{display:inline-block;min-width:42px;color:#6B3FB0}}
li.sub{{font-weight:500;font-size:16px;color:#5b5a52;padding-left:42px;margin-top:-4px}}
</style></head><body><div class="glow"></div><div class="ring"></div>
<div class="wrap"><div class="logo">{b.LOGO_MARK}Abla<sup>IA</sup></div><h1>{h1}</h1><div class="chips">{chips}</div></div>
<div class="bubble">{msg}</div>
<div class="ticket"><div class="t-head"><span>ABLA</span><span>#1042</span></div><div class="t-meta"><span>{e(via)}</span><span>{e(when)}</span></div><ul>{lis}</ul></div>
</body></html>"""

async def main():
    from playwright.async_api import async_playwright
    out = os.path.join(ROOT, "src", "og")
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        exe = next((x for x in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser") if os.path.exists(x)), None)
        br = await p.chromium.launch(**({"executable_path": exe} if exe else {}), args=["--no-sandbox", "--allow-file-access-from-files"])
        pg = await br.new_page(viewport={"width": 1200, "height": 630})
        for l in b.LANGS:
            tmp = os.path.join(out, f".og-{l}.html")
            with open(tmp, "w", encoding="utf-8") as f: f.write(page(l))
            await pg.goto("file://" + tmp)
            await pg.evaluate("document.fonts.ready")
            await pg.wait_for_timeout(150)
            await pg.screenshot(path=os.path.join(out, f"og-{l}.jpg"), type="jpeg", quality=86)   # small enough for WhatsApp previews
            os.remove(tmp)
            print("og image", l)
        await br.close()

if __name__ == "__main__":
    asyncio.run(main())
