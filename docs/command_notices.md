# Last-command notices

Written by Kera (GPT-6 Astra) for Amandeep Jutla. Created 2026-09-19.

This fork prints the last command recorded for each newly restored pane above
the shell prompt:

```text
[resurrect] Last command: codex resume
```

The notice is enabled by default. With the Fish hook below, it remembers the
last command entered in each pane, even after the command finishes. Tracking
is local to that pane; shared shell history is never used to infer a command.
The remembered command survives a restore followed by another save.

For existing snapshots and shells without the hook, it falls back to the
process arguments that Resurrect captured when saving. Those arguments may
differ from what you typed, for example when using a shell alias. A pane with
neither a remembered command nor saved process arguments gets no notice.

## Fish setup

Link the hook into Fish's configuration directory (adjust the plugin path if
you installed elsewhere):

```sh
ln -s ~/.config/tmux/plugins/tmux-resurrect/shell/resurrect.fish \
  ~/.config/fish/conf.d/tmux-resurrect.fish
```

New interactive Fish shells load the hook automatically. In an existing Fish
shell, load it once with:

```fish
source ~/.config/fish/conf.d/tmux-resurrect.fish
```

Tracking starts with the next command entered. The hook uses `fish_preexec`
and a pane-local tmux option, so it also captures commands still running when
you save. It does not record commands while Fish private mode is active;
Resurrect's existing running-process capture still applies separately.
Multiline commands are displayed on one line. Completed-command tracking is
currently provided for Fish only. Additional `command` records in new snapshots
are ignored by upstream Resurrect readers.

## Display behavior

The notice is plain terminal output and remains in scrollback. Saved command
text is printed literally, with control characters replaced by spaces. It is
never executed by this feature or inserted into shell history. Ordinary process
restoration remains controlled separately by `@resurrect-processes`; setting
that to `false` leaves restored panes at a shell prompt.

Existing panes are left running and receive no extra notice on repeated
restoration. ktab sidebar panes are excluded. If pane-content restoration is
enabled, the notice follows the captured contents. A shell startup script that
clears the screen may hide the notice.

To disable notices:

```tmux
set -g @resurrect-show-command 'off'
```

Run the isolated regression check with Fish available on `PATH`:

```sh
micromamba run -n python-base python tests/test_command_notice.py
```
