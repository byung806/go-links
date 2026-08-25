# go-links

Type `go/mail` in your browser and land on Gmail. Short local shortcuts that
redirect `go/<name>` to a full URL.

macOS only — it uses `/etc/hosts` + a `launchd` daemon. Python 3 stdlib, no pip installs.

## install

Clone it somewhere it can stay (the daemon points at this path):

    git clone https://github.com/byung806/go-links.git ~/golink
    cd ~/golink
    chmod +x golink

Install the resolver. This writes the `/etc/hosts` entry and a launchd daemon
on port 80, so it needs sudo:

    sudo ./golink install

## usage

Manage and open links two ways:

- In the browser at `http://go/` or `go/` — ensure the browser navigates
  instead of searching.
- From the CLI:

      ./golink add <name> <url>
      ./golink rm <name>
      ./golink list

## aliases

Two names, one link. `go/76270` and `go/76-270` behave identically, including
every sub-path — `go/76270/markel` resolves exactly like `go/76-270/markel`:

      ./golink alias 76270 76-270

An alias is just a link whose target is `go/<other-name>`, so `add` works too.
The URL box on the go/ page takes the same thing — `go/76-270`, `http://go/76-270`,
`/76-270`, or just `76-270` if that link already exists — no need to type a
full `http://` URL to point one name at another:

      ./golink add 270 go/76-270

Adding a link whose URL exactly matches one you already have folds into an
alias automatically, rather than making a second copy that can drift apart —
`./golink add 76270 <the same url>` becomes `76270 -> go/76-270`. The shorter
existing name is treated as the canonical one.

The canonical link owns the row on `go/`; its aliases show as chips underneath,
and hits through any alias are counted on the canonical link. `rm <alias>`
removes just that alias.

## chrome extension (omnibox + bookmark sync)

Chrome won't autocomplete `go/` URLs on its own: every go link is a redirect,
and Chrome remembers the destination rather than the hop. The commercial go-link
products solve this with a browser extension, and `extension/` is the same idea,
pointed at your local resolver. Load it once:

`chrome://extensions` → Developer mode → **Load unpacked** → pick `extension/`.

It gives you two things, both read live from `go/_links` — nothing is a snapshot:

- **Omnibox keyword.** `go` + Tab + a name, with suggestions as you type,
  aliases marked. Same flow the Trotto and GoLinks extensions use.
- **Bookmark sync.** A `go links` bookmark folder, one entry per link titled
  `go/<name>`. Chrome matches bookmarks by title, so typing a bare `alex`
  surfaces `go/alex` in the normal dropdown — while Google stays your default
  search engine and its suggestions keep working. Re-synced every 5 minutes
  and on browser start; renamed links update, deleted links disappear. If the
  daemon is down a sync is skipped, leaving existing bookmarks untouched.

The endpoint it reads is plain JSON, aliases resolved to their final target:

    curl http://go/_links
    [{"name": "76270", "url": "https://…", "alias": true}, …]

Run `node extension/test_background.js` to exercise the suggestion ranking.

## uninstall

    sudo ./golink uninstall

Removes the `/etc/hosts` line and the daemon. Your links (`~/.golinks/links.json`)
are left alone.
