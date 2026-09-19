# Preserving ktab groups

Integration and documentation by Kera (GPT-6 Astra) for Amandeep Jutla.
Created 2026-09-19.

This fork works with [ktab](https://github.com/amandeepjutla/ktab) to preserve:

- each window's group, including ungrouped windows;
- each session's collapsed groups;
- whether the sidebar is enabled;
- one working sidebar after restoring the saved pane layouts.

Use **prefix + Ctrl-s** to save, then **prefix + Ctrl-r** to restore after a
restart. Make a new save after installing the integration. Existing snapshots
remain readable, but snapshots made before this integration contain no groups.
Automatic saving still requires a separate scheduler such as tmux-continuum.

`@resurrect-processes 'false'` continues to leave application processes stopped.
The sidebar renderer is restored as part of the interface. Existing content
panes are never reclassified as sidebars merely because their indexes match a
saved sidebar position.

## Installation and migration

Install the current ktab version and use this fork in the TPM plugin list:

```tmux
set -g @plugin 'amandeepjutla/tmux-resurrect'
```

If upstream is already installed, changing this line alone leaves its checkout
pointing at upstream. For a clean checkout, change its remote and fast-forward:

```sh
git -C ~/.config/tmux/plugins/tmux-resurrect remote set-url origin \
  https://github.com/amandeepjutla/tmux-resurrect.git
git -C ~/.config/tmux/plugins/tmux-resurrect fetch origin
git -C ~/.config/tmux/plugins/tmux-resurrect merge --ff-only origin/master
tmux source-file ~/.config/tmux/tmux.conf
```

Preserve any local plugin modifications before updating. ktab must be loaded
when saving and restoring. Its plugin registers the installed renderer path
in `@ktab_binary`; no executable path is taken from a saved snapshot.

## Snapshot compatibility

The normal `pane`, `window`, `state`, and `grouped_session` records remain
unchanged. Additional `ktab-pane` records identify saved UI panes, and a
versioned `ktab` JSON record stores group and session state. Names are data,
including quotes, semicolons, and backslashes. Window identity uses the saved
session name and window index, rather than temporary tmux IDs.

Upstream readers ignore the additional records and can restore the ordinary
layout. Full group/sidebar restoration requires both this fork and ktab.
Malformed or unsupported ktab metadata stops restoration before pane changes.
The restore guard is released on normal completion and handled exit signals.

## Regression checks

Build ktab, then run the isolated test from this repository:

```sh
micromamba run -n python-base python tests/test_ktab_restore.py --ktab ../ktab
```

The test uses Python's standard library, a temporary snapshot directory, and a
dedicated tmux socket with a PTY client. It saves, destroys the test server,
starts a new server with ktab already open, and restores. It also covers literal
group names, collapsed active groups, a disabled sidebar, repeated restoration,
running-pane preservation, invalid metadata, and snapshots without ktab.
The live tmux server and its snapshots are untouched.
