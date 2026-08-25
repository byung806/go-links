// Runs on the go/ page. Adding or deleting a link redirects back here, so a
// ping on load keeps the bookmark folder current without waiting 5 minutes.
chrome.runtime.sendMessage({ type: "sync" });
