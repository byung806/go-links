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

- In the browser at `http://go/` — keep the `http://` scheme so Chrome navigates
  instead of running a search.
- From the CLI:

      ./golink add <name> <url>
      ./golink rm <name>
      ./golink list

## uninstall

    sudo ./golink uninstall

Removes the `/etc/hosts` line and the daemon. Your links (`~/.golinks/links.json`)
are left alone.
