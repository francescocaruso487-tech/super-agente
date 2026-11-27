import json, sys
from playwright.sync_api import sync_playwright
B="http://localhost:8765/"
bug=[]; fails404=[]; errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    c=b.new_context(viewport={"width":412,"height":915},service_workers="block")
    pg=c.new_page()
    pg.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.on("pageerror",lambda e: errs.append("PAGEERROR "+str(e)))
    pg.on("response",lambda r: fails404.append((r.status,r.url)) if r.status>=400 else None)
    pg.goto(B); pg.wait_for_timeout(2500)
    print("TITLE",pg.title())
    # tutti i bottoni/chip cliccabili: conta
    btns=pg.eval_on_selector_all("button, [data-nic], [data-tab], .chip", "els=>els.map(e=>({t:(e.innerText||'').trim().slice(0,30),v:!!(e.offsetParent)}))")
    print("CLICCABILI",len(btns),"visibili",sum(1 for x in btns if x['v']))
    # overflow orizzontale
    ov=pg.evaluate("document.documentElement.scrollWidth>document.documentElement.clientWidth")
    print("OVERFLOW_X",ov)
    # click ogni tab inferiore e nicchia
    tabs=pg.query_selector_all("nav button, .bottom button, [data-tab]")
    print("TABS",len(tabs))
    for i in range(len(tabs)):
        try:
            t=pg.query_selector_all("nav button, .bottom button, [data-tab]")[i]
            if not t.is_visible(): continue
            lab=(t.inner_text() or "").strip()[:20]
            t.click(timeout=2000); pg.wait_for_timeout(500)
            print("TAB",i,lab,"ok overflow",pg.evaluate("document.documentElement.scrollWidth>document.documentElement.clientWidth"))
        except Exception as e:
            bug.append(("tab",i,str(e)[:80]))
    print("BUG",bug)
    print("HTTP>=400",fails404)
    print("ERRORI",errs[:10])
    b.close()
