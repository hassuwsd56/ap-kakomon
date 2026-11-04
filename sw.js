// 自動生成（tools/gen_meta.py）。直接編集しない。
const CACHE = 'ap-kakomon-307e833075';
const FILES = ["./", "index.html", "manifest.webmanifest?v=1", "icons/icon-180.png?v=1", "icons/icon-192.png", "icons/icon-512.png", "icons/icon.svg?v=1", "data/exams.json", "data/2025r07a.json", "data/2025r07h.json", "data/2024r06a.json", "data/2024r06h.json", "data/2023r05a.json", "img/2025r07a/q01_1.png", "img/2025r07a/q10_1.png", "img/2025r07a/q15_1.png", "img/2025r07a/q19_1.png", "img/2025r07a/q20_1.png", "img/2025r07a/q22_1.png", "img/2025r07a/q54_1.png", "img/2025r07a/q65_1.png", "img/2025r07a/q70_1.png", "img/2025r07a/q74_1.png", "img/2025r07a/q75_1.png", "img/2025r07a/q76_1.png", "img/2025r07a/q77_1.png", "img/2025r07h/q05_1.png", "img/2025r07h/q06_1.png", "img/2025r07h/q08_1.png", "img/2025r07h/q13_1.png", "img/2025r07h/q16_1.png", "img/2025r07h/q21_1.png", "img/2025r07h/q25_1.png", "img/2025r07h/q27_1.png", "img/2025r07h/q31_1.png", "img/2025r07h/q36_1.png", "img/2025r07h/q43_1.png", "img/2025r07h/q54_1.png", "img/2025r07h/q66_1.png", "img/2025r07h/q69_1.png", "img/2025r07h/q76_1.png", "img/2024r06a/q05_1.png", "img/2024r06a/q14_1.png", "img/2024r06a/q21_1.png", "img/2024r06a/q25_1.png", "img/2024r06a/q28_1.png", "img/2024r06a/q29_1.png", "img/2024r06a/q30_1.png", "img/2024r06a/q72_1.png", "img/2024r06a/q73_1.png", "img/2024r06a/q75_1.png", "img/2024r06a/q77_1.png", "img/2024r06h/q05_1.png", "img/2024r06h/q06_1.png", "img/2024r06h/q08_1.png", "img/2024r06h/q17_1.png", "img/2024r06h/q21_1.png", "img/2024r06h/q22_1.png", "img/2024r06h/q26_1.png", "img/2024r06h/q47_1.png", "img/2024r06h/q51_1.png", "img/2024r06h/q52_1.png", "img/2024r06h/q64_1.png", "img/2024r06h/q75_1.png", "img/2024r06h/q77_1.png", "img/2023r05a/q04_1.png", "img/2023r05a/q05_1.png", "img/2023r05a/q17_1.png", "img/2023r05a/q22_1.png", "img/2023r05a/q23_1.png", "img/2023r05a/q29_1.png", "img/2023r05a/q30_1.png", "img/2023r05a/q53_1.png", "img/2023r05a/q80_1.png"];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  const isPage = e.request.mode === 'navigate' || url.pathname.endsWith('/data/exams.json');
  if (isPage) {
    // 画面と問題一覧はネット優先（更新をすぐ反映）、だめならキャッシュ
    e.respondWith(fetch(e.request).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); return r; })
      .catch(() => caches.match(e.request, {ignoreSearch: true}).then(r => r || caches.match('./'))));
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => {
      if (res.ok) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); }
      return res;
    })));
  }
});
