# ktab integration by Kera (GPT-6 Astra). Created 2026-09-19.
# Optional integration: ordinary resurrect snapshots keep their original format.

KTAB_RESTORE_ACTIVE="false"

ktab_binary() {
	local binary
	binary="$(get_tmux_option "@ktab_binary" "")"
	[ -n "$binary" ] && [ -x "$binary" ] && printf '%s\n' "$binary"
}

ktab_save_state() {
	local binary
	if binary="$(ktab_binary)"; then
		"$binary" resurrect save "$1"
	fi
}

ktab_saved_sidebar() {
	local record
	printf -v record 'ktab-pane\t%s\t%s\t%s' "$1" "$2" "$3"
	grep -Fqx -- "$record" "$(last_resurrect_file)"
}

ktab_prepare_restore() {
	local binary
	if grep -q $'^ktab\t' "$(last_resurrect_file)" && binary="$(ktab_binary)"; then
		KTAB_RESTORE_ACTIVE="true"
		"$binary" resurrect prepare "$(last_resurrect_file)"
	fi
}

ktab_finish_restore() {
	local binary
	if [ "$KTAB_RESTORE_ACTIVE" = "true" ]; then
		binary="$(ktab_binary)" || return 1
		"$binary" resurrect restore "$(last_resurrect_file)" || return 1
		KTAB_RESTORE_ACTIVE="false"
	fi
}

ktab_resume_restore() {
	local binary
	if [ "$KTAB_RESTORE_ACTIVE" = "true" ] && [ "$(get_tmux_option '@ktab_restoring' '')" = "1" ]; then
		if binary="$(ktab_binary)"; then
			"$binary" resurrect resume
		else
			tmux set-option -gqu @ktab_restoring
		fi
		KTAB_RESTORE_ACTIVE="false"
	fi
}
