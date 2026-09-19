# Kera (GPT-6 Astra). Created 2026-09-19.
# Optional shell metadata; upstream readers ignore these extra records.

save_last_command() {
	local session_name="$1" window_number="$2" pane_index="$3"
	local command
	command="$(tmux show-option -pqv -t "${session_name}:${window_number}.${pane_index}" \
		@resurrect-last-command 2>/dev/null)"
	if [ -n "$command" ]; then
		command="$(printf '%s' "$command" | LC_ALL=C tr '\000-\037\177' ' ')"
		printf 'command\t%s\t%s\t%s\t:%s\n' "$session_name" "$window_number" "$pane_index" "$command"
	fi
}

saved_last_command() {
	local kind session_name window_number pane_index command
	while IFS=$'\t' read -r kind session_name window_number pane_index command; do
		if [ "$session_name" = "$1" ] && [ "$window_number" = "$2" ] && [ "$pane_index" = "$3" ]; then
			printf '%s' "${command#:}"
			return
		fi
	done < <(grep $'^command\t' "$(last_resurrect_file)")
}
