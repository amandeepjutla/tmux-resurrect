#!/usr/bin/env bash
# Kera (GPT-6 Astra). Created 2026-09-19.
# Saved process arguments are display-only; never evaluate them as shell input.

saved_command="$1"
default_shell="$2"
default_command="$3"
contents="$4"

if [ -n "$contents" ] && [ -f "$contents" ]; then
	cat -- "$contents"
fi

# Flatten control characters, including embedded newlines and terminal escapes.
saved_command="$(printf '%s' "$saved_command" | LC_ALL=C tr '\000-\037\177' ' ')"
printf '[resurrect] Last command: %s\n\n' "$saved_command"

if [ -n "$default_command" ]; then
	exec "$default_shell" -c "$default_command"
else
	# Match tmux's empty default-command behavior: a login shell.
	exec -a "-$(basename "$default_shell")" "$default_shell"
fi
