# ktab integration by Kera (GPT-6 Astra). Created 2026-09-19.
# Optional integration: ordinary resurrect snapshots keep their original format.
# 2026-09-24: Scratchpad save preparation by Kera (GPT-6 Sol).

KTAB_RESTORE_ACTIVE="false"
KTAB_SCRATCH_SAVE_SESSIONS=()

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

ktab_prepare_save() {
	local binary session visible
	binary="$(ktab_binary)" || return 0
	while read -r session visible; do
		[ "$visible" = "1" ] || continue
		KTAB_SCRATCH_SAVE_SESSIONS+=("$session")
		tmux set-option -t "$session" @ktab_scratch_saved_visible 1 || return 1
		"$binary" scratch park "$session" || return 1
	done < <(tmux list-sessions -F '#{session_id} #{@ktab_scratch_visible}')
}

ktab_finish_save() {
	local binary session current
	[ "${#KTAB_SCRATCH_SAVE_SESSIONS[@]}" -gt 0 ] || return 0
	binary="$(ktab_binary)" || return 1
	for session in "${KTAB_SCRATCH_SAVE_SESSIONS[@]}"; do
		# Selecting window 0 during a save is an explicit request to keep the
		# scratchpad there; otherwise restore the right-hand view.
		current="$(tmux display-message -p -t "$session" '#{window_index}')" || return 1
		if [ "$current" != "0" ]; then
			"$binary" scratch show "$session" || return 1
		fi
		tmux set-option -qu -t "$session" @ktab_scratch_saved_visible || return 1
	done
	KTAB_SCRATCH_SAVE_SESSIONS=()
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
