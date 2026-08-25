// Talks to the local resolver (http://go/_links) so both features below are
// always current — nothing here is a snapshot of your links.
const API = "http://go/_links";
const FOLDER = "go links";
const SYNC_MINUTES = 5;

async function fetchLinks() {
  const resp = await fetch(API, { cache: "no-store" });
  if (!resp.ok) throw new Error(`go daemon: HTTP ${resp.status}`);
  return resp.json();
}

// --- omnibox: "go" + Tab, the way the commercial extensions do it ---------

function score(link, q) {
  const name = link.name.toLowerCase();
  if (!q) return 0;
  if (name === q) return 0;
  if (name.startsWith(q)) return 1;
  if (name.includes(q)) return 2;
  return -1;
}

function match(links, query) {
  const q = query.trim().toLowerCase();
  return links
    .map((l) => ({ link: l, rank: score(l, q) }))
    .filter((r) => r.rank >= 0)
    .sort((a, b) => a.rank - b.rank || a.link.name.length - b.link.name.length)
    .slice(0, 8)
    .map((r) => r.link);
}

const escapeXml = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
   .replace(/"/g, "&quot;");

if (globalThis.chrome?.omnibox) {
chrome.omnibox.onInputChanged.addListener(async (text, suggest) => {
  let links = [];
  try {
    links = await fetchLinks();
  } catch (e) {
    suggest([{ content: text, description: `go daemon unreachable — ${escapeXml(String(e.message))}` }]);
    return;
  }
  suggest(
    match(links, text).map((l) => ({
      content: l.name,
      description:
        `<match>go/${escapeXml(l.name)}</match>` +
        (l.alias ? " <dim>(alias)</dim>" : "") +
        ` <url>${escapeXml(l.url)}</url>`,
    }))
  );
});

chrome.omnibox.onInputEntered.addListener((text, disposition) => {
  const url = "http://go/" + text.trim().replace(/^\/+/, "");
  if (disposition === "newForegroundTab") chrome.tabs.create({ url });
  else if (disposition === "newBackgroundTab") chrome.tabs.create({ url, active: false });
  else chrome.tabs.update({ url });
});

// --- bookmark sync: what makes a bare "alex" autocomplete ----------------
// Chrome's omnibox matches bookmarks by title, so each link gets a bookmark
// titled "go/<name>". Re-synced on a timer, so it never goes stale.

async function folderId() {
  const [existing] = await chrome.bookmarks.search({ title: FOLDER });
  if (existing && !existing.url) return existing.id;
  const other = (await chrome.bookmarks.getTree())[0].children.find(
    (c) => c.id === "2" || /other/i.test(c.title)
  );
  const made = await chrome.bookmarks.create({
    parentId: other ? other.id : undefined,
    title: FOLDER,
  });
  return made.id;
}

async function syncBookmarks() {
  let links;
  try {
    links = await fetchLinks();
  } catch (e) {
    console.warn("go links: sync skipped —", e.message);
    return; // daemon down: leave the existing bookmarks alone
  }
  const parentId = await folderId();
  const have = new Map(
    (await chrome.bookmarks.getChildren(parentId)).map((b) => [b.title, b])
  );
  const want = new Map(links.map((l) => [`go/${l.name}`, `http://go/${l.name}`]));

  for (const [title, url] of want) {
    const bm = have.get(title);
    if (!bm) await chrome.bookmarks.create({ parentId, title, url });
    else if (bm.url !== url) await chrome.bookmarks.update(bm.id, { url });
  }
  for (const [title, bm] of have) {
    if (!want.has(title)) await chrome.bookmarks.remove(bm.id); // link deleted
  }
  await chrome.storage.local.set({ lastSync: Date.now(), count: want.size });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("sync", { periodInMinutes: SYNC_MINUTES });
  syncBookmarks();
});
chrome.runtime.onStartup.addListener(syncBookmarks);
// The go/ page pings us after any add or delete, so UI edits land at once
// instead of waiting for the next alarm.
chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
  if (msg?.type !== "sync") return;
  syncBookmarks().then(() => respond({ ok: true }));
  return true; // respond asynchronously
});
chrome.alarms.onAlarm.addListener((a) => a.name === "sync" && syncBookmarks());
}

// Lets the ranking be tested outside Chrome (node test_background.js).
if (typeof module !== "undefined") module.exports = { match, score };
