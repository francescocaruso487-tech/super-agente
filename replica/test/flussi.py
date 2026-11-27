from playwright.sync_api import sync_playwright
res=[];errs=[]
def ok(n,c,d=""): res.append(("OK " if c else "KO ")+n+(" "+d if d else ""))
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    pg=b.new_context(viewport={"width":412,"height":915},service_workers="block").new_page()
    pg.set_default_timeout(3000)
    pg.on("pageerror",lambda e: errs.append(str(e)[:100]))
    pg.goto("http://localhost:8765/"); pg.wait_for_timeout(3000)
    for i in range(4):
        pg.locator("#nicchie button").nth(i).click(); pg.wait_for_timeout(700)
        lab=pg.locator("#nicchie button").nth(i).inner_text().strip()[:14]
        for _ in range(4):
            if pg.locator("article.card").locator("visible=true").count(): break
            c=pg.locator("#lista-novita [aria-expanded=false]").locator("visible=true")
            if not c.count(): break
            c.first.click(); pg.wait_for_timeout(500)
        n=pg.locator("article.card").locator("visible=true").count()
        opened=False
        if n:
            pg.locator("article.card").locator("visible=true").first.click(); pg.wait_for_timeout(600)
            opened=pg.locator("#pop .pop-t").count()>0
            if opened:
                t=pg.locator("#pop .pop-c").inner_text()
                ok(f"{lab}: scheda con Apri e Salva","Apri" in t and "Salva" in t)
            pg.locator("#pop .pop-x").click(); pg.wait_for_timeout(300)
        ok(f"{lab}: {n} card, scheda apribile",n>0 and opened)
    pg.locator("[data-tab=archivio]").click(); pg.wait_for_timeout(500)
    pg.fill("#cerca","superbonus"); pg.wait_for_timeout(900)
    k=pg.locator("#lista-archivio article.card").count()
    ok("ricerca 'superbonus'",k>0,str(k))
    pg.fill("#cerca","zzzzqq"); pg.wait_for_timeout(700)
    ok("ricerca senza risultati",pg.locator("#lista-archivio article.card").count()==0,pg.locator("#lista-archivio").inner_text()[:50].replace("\n"," "))
    ok("errori JS",not errs,str(errs))
    b.close()
print("\n".join(res))
