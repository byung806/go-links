# go-links

Type `go/mail` in your browser and land on Gmail. Short local shortcuts that
redirect `go/<name>` to a full URL.

macOS only — it uses `/etc/hosts` + a `launchd` daemon. Python 3 stdlib, no pip installs.

## install

Clone it somewhere it can stay (the daemon points at this path):

    git clone https://github.com/byung806/go-links.git ~/golink
    cd ~/golink
    chmod +x golink

Add a couple links:

    ./golink add mail https://mail.google.com
    ./golink add gh https://github.com/byung806

Install the resolver. This writes the `/etc/hosts` entry and a launchd daemon
on port 80, so it needs sudo:

    sudo ./golink install

Done. Open `http://go/mail` in a browser.

## usage

    ./golink add <name> <url>    add or update a link
    ./golink rm <name>           remove a link
    ./golink list                list everything

Or manage links in the browser at `http://go/`.

Paths pass through: with `gh -> https://github.com`, going to `go/gh/byung806`
sends you to `https://github.com/byung806`.

## chrome

Typing a bare `go/mail` in Chrome's address bar sometimes searches instead of
navigating (single-word hostname). Two fixes:

- type it with the scheme: `http://go/mail`
- or add a site search in Settings > Search engines: shortcut `go`, URL `http://go/%s`

## run from anywhere (optional)

    sudo ln -s ~/golink/golink /usr/local/bin/golink

Then `golink add ...` works from any directory.

## uninstall

    sudo ./golink uninstall

Removes the `/etc/hosts` line and the daemon. Your links (`~/.golinks/links.json`)
are left alone.
