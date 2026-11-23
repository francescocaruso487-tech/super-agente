// Service worker: l'app si apre anche offline con le ultime notizie salvate.
const VERSIONE = "v55";
const SHELL = ["./", "index.html", "style.css", "app.js", "link.js", "theme.js", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSIONE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSIONE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  const isData = req.url.includes("/data/");
  e.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(VERSIONE).then((c) => c.put(req, copy));
      return res;
    }).catch(() => caches.match(req).then((m) => m || (isData ? new Response("{}", { headers: { "content-type": "application/json" } }) : caches.match("index.html"))))
  );
});
