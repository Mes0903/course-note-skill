#!/usr/bin/env bash
set -euo pipefail
COURSE_NOTES_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
COURSE_NOTES_REPO_ROOT="$(cd -- "$COURSE_NOTES_SCRIPT_DIR/.." && pwd -P)"
source "$COURSE_NOTES_SCRIPT_DIR/versions.env"
COURSE_NOTES_TOOLS_DIR="$COURSE_NOTES_REPO_ROOT/.tools"
COURSE_NOTES_UV_DIR="$COURSE_NOTES_REPO_ROOT/.tools/uv"
COURSE_NOTES_UV_BIN="$COURSE_NOTES_UV_DIR/uv"

course_notes_uv_is_pinned() {
  local course_notes_uv_bin="$1"
  local course_notes_uv_output course_notes_uv_name course_notes_uv_version
  [[ -f "$course_notes_uv_bin" && ! -L "$course_notes_uv_bin" \
    && -x "$course_notes_uv_bin" ]] || return 1
  if ! course_notes_uv_output="$("$course_notes_uv_bin" --version 2>/dev/null)"; then
    return 1
  fi
  [[ -n "$course_notes_uv_output" ]] || return 1
  read -r course_notes_uv_name course_notes_uv_version _ <<< "$course_notes_uv_output"
  [[ "$course_notes_uv_name" == "uv" && "$course_notes_uv_version" == "$UV_VERSION" ]]
}

if course_notes_uv_is_pinned "$COURSE_NOTES_UV_BIN"; then
  exit 0
fi

umask 077
mkdir -p -- "$COURSE_NOTES_TOOLS_DIR"
COURSE_NOTES_UV_STAGING="$(mktemp -d "$COURSE_NOTES_TOOLS_DIR/.uv-staging.XXXXXXXX")"
chmod 0700 -- "$COURSE_NOTES_UV_STAGING"
COURSE_NOTES_UV_BACKUP=""
COURSE_NOTES_UV_OLD_MOVED=false
COURSE_NOTES_UV_ARCHIVE="uv-${UV_TARGET}.tar.gz"

course_notes_uv_cleanup() {
  rm -rf -- "$COURSE_NOTES_UV_STAGING"
}

course_notes_uv_restore() {
  if [[ -e "$COURSE_NOTES_UV_DIR" || -L "$COURSE_NOTES_UV_DIR" ]]; then
    if ! mv -T -- "$COURSE_NOTES_UV_DIR" "$COURSE_NOTES_UV_STAGING/failed-uv"; then
      echo "course-notes: uv restoration failed; recovery backup preserved at ${COURSE_NOTES_UV_BACKUP#"$COURSE_NOTES_REPO_ROOT/"}" >&2
      return 1
    fi
  fi
  if ! mv -T -- "$COURSE_NOTES_UV_BACKUP/uv" "$COURSE_NOTES_UV_DIR"; then
    echo "course-notes: uv restoration failed; recovery backup preserved at ${COURSE_NOTES_UV_BACKUP#"$COURSE_NOTES_REPO_ROOT/"}" >&2
    return 1
  fi
  COURSE_NOTES_UV_OLD_MOVED=false
  rm -rf -- "$COURSE_NOTES_UV_BACKUP"
  COURSE_NOTES_UV_BACKUP=""
}

trap course_notes_uv_cleanup EXIT
curl --fail --location --proto '=https' --tlsv1.2 \
  "https://releases.astral.sh/github/uv/releases/download/$UV_VERSION/$COURSE_NOTES_UV_ARCHIVE" \
  --output "$COURSE_NOTES_UV_STAGING/$COURSE_NOTES_UV_ARCHIVE"
(
  cd -- "$COURSE_NOTES_UV_STAGING"
  printf '%s  %s\n' "$UV_SHA256" "$COURSE_NOTES_UV_ARCHIVE" | sha256sum -c -
)
tar -xzf "$COURSE_NOTES_UV_STAGING/$COURSE_NOTES_UV_ARCHIVE" \
  -C "$COURSE_NOTES_UV_STAGING"
COURSE_NOTES_UV_NEXT="$COURSE_NOTES_UV_STAGING/uv-${UV_TARGET}"
course_notes_uv_is_pinned "$COURSE_NOTES_UV_NEXT/uv" || {
  echo "course-notes: downloaded uv has the wrong version" >&2
  exit 1
}

if [[ -e "$COURSE_NOTES_UV_DIR" || -L "$COURSE_NOTES_UV_DIR" ]]; then
  COURSE_NOTES_UV_BACKUP="$(mktemp -d "$COURSE_NOTES_TOOLS_DIR/.uv-backup.XXXXXXXX")"
  chmod 0700 -- "$COURSE_NOTES_UV_BACKUP"
  if ! mv -T -- "$COURSE_NOTES_UV_DIR" "$COURSE_NOTES_UV_BACKUP/uv"; then
    echo "course-notes: unable to back up the existing uv" >&2
    exit 1
  fi
  COURSE_NOTES_UV_OLD_MOVED=true
fi

if ! mv -T -- "$COURSE_NOTES_UV_NEXT" "$COURSE_NOTES_UV_DIR"; then
  if [[ "$COURSE_NOTES_UV_OLD_MOVED" == true ]]; then
    course_notes_uv_restore || exit 1
  fi
  echo "course-notes: unable to publish uv" >&2
  exit 1
fi
if ! course_notes_uv_is_pinned "$COURSE_NOTES_UV_BIN"; then
  if [[ "$COURSE_NOTES_UV_OLD_MOVED" == true ]]; then
    course_notes_uv_restore || exit 1
  else
    mv -T -- "$COURSE_NOTES_UV_DIR" "$COURSE_NOTES_UV_STAGING/failed-uv" || true
  fi
  echo "course-notes: published uv failed verification" >&2
  exit 1
fi

if [[ "$COURSE_NOTES_UV_OLD_MOVED" == true ]]; then
  COURSE_NOTES_UV_OLD_MOVED=false
  rm -rf -- "$COURSE_NOTES_UV_BACKUP"
  COURSE_NOTES_UV_BACKUP=""
fi
