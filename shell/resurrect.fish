# Kera (GPT-6 Astra). Created 2026-09-19.
# Load from Fish's conf.d directory to remember each tmux pane's last command.
status is-interactive; or return

function __resurrect_last_command --on-event fish_preexec
    set -q TMUX TMUX_PANE; or return
    test -n "$fish_private_mode"; and return
    set -l last_command (string replace --all --regex '[[:cntrl:]]' ' ' -- "$argv[1]")
    command tmux set-option -pq -t "$TMUX_PANE" @resurrect-last-command "$last_command" 2>/dev/null
end
