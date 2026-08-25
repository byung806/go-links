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

## go/ as your default search engine

The resolver falls through to a web search for anything that isn't a link, so
it can be Chrome's default engine — then a bare `alex` in the address bar goes
to `go/alex`, and `how tall is everest` goes to Google.

`chrome://settings/searchEngines` → Site search → Add:

    Name      go
    Shortcut  go
    URL       http://go/%s

then ⋮ → Make default. (Chrome only offers custom-engine suggestions in
keyword mode, which is why a bare name shows nothing until go/ *is* the
default.)

To search somewhere other than Google, add a link named `_search` whose URL
contains `%s`:

    ./golink add _search 'https://duckduckgo.com/?q=%s'

It's hidden from the go/ list. Note the trade-off: with go/ as the default
engine, every search you type goes through the local daemon, so if it's down
the address bar errors instead of searching, and a typo like `mial` becomes a
web search rather than a 404.

## uninstall

    sudo ./golink uninstall

Removes the `/etc/hosts` line and the daemon. Your links (`~/.golinks/links.json`)
are left alone.
