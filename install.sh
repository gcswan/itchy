#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd
)"

INSTALL_MODE="symlink"
ASSUME_YES=0
declare -a SELECTED_TOOLS=()

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Install all skills (directories containing SKILL.md) into one or more CLI
skill directories.

Options:
  --copy            Copy skills instead of symlinking them
  --yes             Replace existing installs without prompting
  --tool TOOL       Install for a specific tool: claude, gemini, codex
  --help            Show this help text

If no --tool flags are provided, the script prompts interactively.
EOF
}

log() {
  printf '%s\n' "$*"
}

warn() {
  printf 'Warning: %s\n' "$*" >&2
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

tool_detected_label() {
  local tool="$1"

  case "$tool" in
    claude)
      has_command claude && printf 'detected' || printf 'not detected'
      ;;
    gemini)
      has_command gemini && printf 'detected' || printf 'not detected'
      ;;
    codex)
      has_command codex && printf 'detected' || printf 'not detected'
      ;;
    *)
      printf 'unknown'
      ;;
  esac
}

normalize_tool() {
  case "$1" in
    claude|claude-code)
      printf 'claude'
      ;;
    gemini|gemini-cli)
      printf 'gemini'
      ;;
    codex)
      printf 'codex'
      ;;
    *)
      return 1
      ;;
  esac
}

tool_destination_root() {
  case "$1" in
    claude)
      printf '%s/.claude/skills' "$HOME"
      ;;
    gemini)
      printf '%s/.gemini/skills' "$HOME"
      ;;
    codex)
      printf '%s/skills' "${CODEX_HOME:-$HOME/.codex}"
      ;;
    *)
      return 1
      ;;
  esac
}

tool_display_name() {
  case "$1" in
    claude)
      printf 'Claude Code'
      ;;
    gemini)
      printf 'Gemini CLI'
      ;;
    codex)
      printf 'Codex CLI'
      ;;
    *)
      return 1
      ;;
  esac
}

prompt_yes_no() {
  local prompt="$1"
  local default_answer="${2:-y}"
  local suffix
  local reply

  if [[ "$default_answer" == "y" ]]; then
    suffix='[Y/n]'
  else
    suffix='[y/N]'
  fi

  while true; do
    printf '%s %s ' "$prompt" "$suffix"
    read -r reply || return 1
    reply="${reply:-$default_answer}"

    case "$reply" in
      y|Y|yes|YES)
        return 0
        ;;
      n|N|no|NO)
        return 1
        ;;
    esac

    log 'Please answer y or n.'
  done
}

prompt_for_tools() {
  local tool
  local display_name
  local destination
  local detection

  log "Install skills for these CLI tools:"

  for tool in claude gemini codex; do
    display_name="$(tool_display_name "$tool")"
    destination="$(tool_destination_root "$tool")"
    detection="$(tool_detected_label "$tool")"

    if prompt_yes_no "Install for $display_name ($destination, $detection)?" y; then
      SELECTED_TOOLS+=("$tool")
    fi
  done
}

remove_existing_destination() {
  local destination="$1"

  if [[ ! -e "$destination" && ! -L "$destination" ]]; then
    return 0
  fi

  rm -rf "$destination"
}

install_skill() {
  local skill_dir="$1"
  local tool="$2"
  local skill_name
  local display_name
  local destination_root
  local destination
  local existing_target

  skill_name="$(basename "$skill_dir")"
  display_name="$(tool_display_name "$tool")"
  destination_root="$(tool_destination_root "$tool")"
  destination="$destination_root/$skill_name"

  mkdir -p "$destination_root"

  if [[ -L "$destination" ]]; then
    existing_target="$(readlink "$destination")"
    if [[ "$existing_target" == "$skill_dir" ]]; then
      log "$display_name: $skill_name already installed at $destination"
      return 0
    fi
  fi

  if [[ -e "$destination" || -L "$destination" ]]; then
    if [[ "$ASSUME_YES" -eq 0 ]]; then
      if ! prompt_yes_no "$display_name already has $skill_name at $destination. Replace it?" n; then
        log "$display_name: $skill_name skipped"
        return 0
      fi
    fi

    remove_existing_destination "$destination"
  fi

  if [[ "$INSTALL_MODE" == "copy" ]]; then
    cp -R "$skill_dir" "$destination"
  else
    ln -s "$skill_dir" "$destination"
  fi

  log "$display_name: installed $skill_name to $destination"
}

parse_args() {
  local normalized

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --copy)
        INSTALL_MODE="copy"
        shift
        ;;
      --yes)
        ASSUME_YES=1
        shift
        ;;
      --tool)
        [[ $# -ge 2 ]] || die "--tool requires a value"
        normalized="$(normalize_tool "$2")" || die "unsupported tool: $2"
        SELECTED_TOOLS+=("$normalized")
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        die "unknown option: $1"
        ;;
    esac
  done
}

dedupe_tools() {
  local tool
  local seen=" "
  local deduped=()

  for tool in "${SELECTED_TOOLS[@]}"; do
    if [[ "$seen" != *" $tool "* ]]; then
      deduped+=("$tool")
      seen+="$(printf '%s ' "$tool")"
    fi
  done

  SELECTED_TOOLS=("${deduped[@]}")
}

discover_skills() {
  local dir
  local skills=()

  for dir in "$SCRIPT_DIR"/*/; do
    if [[ -f "$dir/SKILL.md" ]]; then
      skills+=("$(cd "$dir" && pwd)")
    fi
  done

  printf '%s\n' "${skills[@]}"
}

main() {
  local skill_dirs
  mapfile -t skill_dirs < <(discover_skills)

  if [[ "${#skill_dirs[@]}" -eq 0 ]]; then
    die "No skills found (no directories with SKILL.md)"
  fi

  log "Found skills: $(printf '%s ' "${skill_dirs[@]}" | xargs -n1 basename | paste -sd', ' -)"

  parse_args "$@"

  if [[ "${#SELECTED_TOOLS[@]}" -eq 0 ]]; then
    prompt_for_tools
  fi

  dedupe_tools

  if [[ "${#SELECTED_TOOLS[@]}" -eq 0 ]]; then
    log 'No tools selected. Nothing to install.'
    exit 0
  fi

  log "Install mode: $INSTALL_MODE"

  for skill_dir in "${skill_dirs[@]}"; do
    for tool in "${SELECTED_TOOLS[@]}"; do
      install_skill "$skill_dir" "$tool"
    done
  done

  log ''
  log 'Done.'
}

main "$@"
