// Plain node test for the omnibox ranking — run: node test_background.js
const assert = require("assert");
const { match } = require("./background.js");

const links = [
  { name: "mail", url: "https://mail.google.com", alias: false },
  { name: "markel", url: "https://drive.google.com/x", alias: true },
  { name: "76-270/markel", url: "https://drive.google.com/x", alias: false },
  { name: "me", url: "https://bryan-yung.com", alias: false },
  { name: "gmail", url: "https://mail.google.com", alias: true },
];

// exact match first, then prefix, then substring; shorter names break ties
assert.deepStrictEqual(match(links, "ma").map((l) => l.name),
  ["mail", "markel", "gmail", "76-270/markel"]);
assert.deepStrictEqual(match(links, "mail").map((l) => l.name),
  ["mail", "gmail"]);
assert.deepStrictEqual(match(links, "MARKEL").map((l) => l.name),
  ["markel", "76-270/markel"]);
assert.deepStrictEqual(match(links, "zzz"), []);
assert.ok(match(links, "m").length <= 8);

console.log("extension ranking tests passed");
