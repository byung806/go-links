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

## omnibox autocomplete

Chrome won't learn `go/` URLs from history — every go link is a redirect, and
Chrome remembers the destination, not the hop. So the resolver advertises
itself as a search engine instead: visiting `go/` lets Chrome discover
`go/_opensearch.xml`, which registers `go` as a keyword and points at a
suggestions endpoint (`go/_suggest?q=`) that completes your link names,
aliases included, ranked by hit count.

Chrome files discovered engines under **Inactive shortcuts** in
`chrome://settings/searchEngines` — activate `go` once, then `go` + Tab +
`mail` works from the address bar. (Arc's omnibox re-offers what you typed,
so it appears to work there without any of this.)

## uninstall

    sudo ./golink uninstall

Removes the `/etc/hosts` line and the daemon. Your links (`~/.golinks/links.json`)
are left alone.
