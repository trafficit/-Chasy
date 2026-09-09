// Network passthrough — no caching.
// (Kept only so browsers that installed an earlier caching version of this
//  file replace it, wipe the old caches, and stop serving stale assets.)

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      await self.clients.claim();
      // one-time refresh for pages that were showing cached content
      const windows = await self.clients.matchAll({ type: "window" });
      for (const client of windows) {
        try {
          client.navigate(client.url);
        } catch (_) {}
      }
    })()
  );
});

// no "fetch" handler -> the browser handles every request normally
