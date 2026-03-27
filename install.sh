#!/usr/bin/env bash
# Install or update moon-skills in a host repository, then run ./setup.
#
# From the host repo root (first install or update):
#   curl -fsSL https://raw.githubusercontent.com/CCharlesMeng/moon-skills/main/install.sh | bash -s -- --host auto --bundle workflow --write
#
# If you already have a checkout:
#   bash .cursor/skills/moon-skills/install.sh --host auto --bundle workflow --write
#
# Override install location (absolute or relative to current directory).
# With curl | bash, pass the variable to the right-hand shell, e.g.:
#   curl -fsSL ... | env MOON_SKILLS_PATH=.agents/skills/moon-skills bash -s -- --write
set -euo pipefail

REPO_URL="${MOON_SKILLS_REPO_URL:-https://github.com/CCharlesMeng/moon-skills.git}"

resolve_target() {
	if [[ -n "${MOON_SKILLS_PATH:-}" ]]; then
		local p="$MOON_SKILLS_PATH"
		case "$p" in
		/*) echo "$p" ;;
		*) echo "$(pwd)/$p" ;;
		esac
		return
	fi

	local src="${BASH_SOURCE[0]:-}"
	if [[ -n "$src" && -f "$src" ]]; then
		local here
		here="$(cd "$(dirname "$src")" && pwd)"
		if [[ -f "$here/setup" ]]; then
			echo "$here"
			return
		fi
	fi

	echo "$(pwd)/.cursor/skills/moon-skills"
}

to_absolute() {
	local t="$1"
	case "$t" in
	/*) echo "$t" ;;
	*) echo "$(pwd)/$t" ;;
	esac
}

clone_or_pull() {
	local target="$1"
	if [[ -d "$target/.git" ]]; then
		git -C "$target" pull --ff-only
		return
	fi

	if [[ ! -e "$target" ]]; then
		mkdir -p "$(dirname "$target")"
		git clone "$REPO_URL" "$target"
		return
	fi

	if [[ -f "$target" ]]; then
		echo "fatal: '$target' exists and is a file, not a directory." >&2
		exit 1
	fi

	if [[ ! -d "$target" ]]; then
		echo "fatal: '$target' exists and is not a directory." >&2
		exit 1
	fi

	# Directory exists but is not a git checkout (e.g. old manual copy). Preserve it and clone fresh.
	local bak="${target}.moon-skills-backup.$(date +%Y%m%d%H%M%S)"
	echo "install.sh: '$target' is not a git clone; moving aside to:" >&2
	echo "  $bak" >&2
	mv "$target" "$bak"
	mkdir -p "$(dirname "$target")"
	git clone "$REPO_URL" "$target"
}

TARGET="$(resolve_target)"
TARGET="$(to_absolute "$TARGET")"
clone_or_pull "$TARGET"
exec "$TARGET/setup" "$@"
