#!/usr/bin/env bash
set -euo pipefail

COURSE_NOTES_REPO_ROOT="${1:?course-notes: installer arguments are invalid}"
COURSE_NOTES_INSTALL_DEVICE="${COURSE_NOTES_INSTALL_DEVICE:-auto}"

cd -- "$COURSE_NOTES_REPO_ROOT"
scripts/bootstrap-uv.sh
source scripts/versions.env

COURSE_NOTES_DENO_DIR="$COURSE_NOTES_REPO_ROOT/.tools/deno"
COURSE_NOTES_DENO_BIN="$COURSE_NOTES_DENO_DIR/deno"

course_notes_deno_is_pinned() {
  local course_notes_output course_notes_name course_notes_version
  [[ -f "$COURSE_NOTES_DENO_BIN" && ! -L "$COURSE_NOTES_DENO_BIN" \
    && -x "$COURSE_NOTES_DENO_BIN" ]] || return 1
  course_notes_output="$("$COURSE_NOTES_DENO_BIN" --version 2>/dev/null)" || return 1
  read -r course_notes_name course_notes_version _ \
    <<< "${course_notes_output%%$'\n'*}"
  [[ "$course_notes_name" == deno && "$course_notes_version" == "$DENO_VERSION" ]]
}

if ! course_notes_deno_is_pinned; then
  mkdir -p -- "$COURSE_NOTES_REPO_ROOT/.tools"
  COURSE_NOTES_DENO_STAGING="$(mktemp -d "$COURSE_NOTES_REPO_ROOT/.tools/.deno-staging.XXXXXXXX")"
  trap 'rm -rf -- "$COURSE_NOTES_DENO_STAGING"' EXIT
  COURSE_NOTES_DENO_ARCHIVE="deno-$DENO_TARGET.zip"
  COURSE_NOTES_DENO_BASE="https://github.com/denoland/deno/releases/download/v$DENO_VERSION"
  curl --fail --location --proto '=https' --tlsv1.2 \
    "$COURSE_NOTES_DENO_BASE/$COURSE_NOTES_DENO_ARCHIVE" \
    --output "$COURSE_NOTES_DENO_STAGING/$COURSE_NOTES_DENO_ARCHIVE"
  curl --fail --location --proto '=https' --tlsv1.2 \
    "$COURSE_NOTES_DENO_BASE/$COURSE_NOTES_DENO_ARCHIVE.sha256sum" \
    --output "$COURSE_NOTES_DENO_STAGING/$COURSE_NOTES_DENO_ARCHIVE.sha256sum"
  (
    cd -- "$COURSE_NOTES_DENO_STAGING"
    sha256sum -c "$COURSE_NOTES_DENO_ARCHIVE.sha256sum"
  )
  mkdir -p -- "$COURSE_NOTES_DENO_STAGING/next"
  unzip -q "$COURSE_NOTES_DENO_STAGING/$COURSE_NOTES_DENO_ARCHIVE" \
    -d "$COURSE_NOTES_DENO_STAGING/next"
  COURSE_NOTES_DENO_BIN="$COURSE_NOTES_DENO_STAGING/next/deno"
  course_notes_deno_is_pinned || {
    echo "course-notes: downloaded Deno has the wrong version" >&2
    exit 1
  }
  rm -rf -- "$COURSE_NOTES_DENO_DIR"
  mv -- "$COURSE_NOTES_DENO_STAGING/next" "$COURSE_NOTES_DENO_DIR"
  COURSE_NOTES_DENO_BIN="$COURSE_NOTES_DENO_DIR/deno"
fi

COURSE_NOTES_SYNC_DEVICE="$COURSE_NOTES_INSTALL_DEVICE"
if [[ "$COURSE_NOTES_SYNC_DEVICE" == auto ]]; then
  if [[ -e /dev/dxg ]] || { command -v nvidia-smi >/dev/null && nvidia-smi >/dev/null; }; then
    COURSE_NOTES_SYNC_DEVICE=cuda
  else
    COURSE_NOTES_SYNC_DEVICE=cpu
  fi
fi
COURSE_NOTES_SYNC_ARGS=(sync --locked)
if [[ "$COURSE_NOTES_SYNC_DEVICE" == cuda ]]; then
  COURSE_NOTES_SYNC_ARGS+=(--extra cuda)
fi
scripts/uv "${COURSE_NOTES_SYNC_ARGS[@]}"

for COURSE_NOTES_COMMAND in bash curl sha256sum unzip ffmpeg ffprobe; do
  command -v "$COURSE_NOTES_COMMAND" >/dev/null || {
    echo "course-notes: required command is unavailable" >&2
    exit 1
  }
done
course_notes_deno_is_pinned || {
  echo "course-notes: pinned Deno is unavailable" >&2
  exit 1
}
if [[ ! -x .venv/bin/course-notes ]] || ! .venv/bin/course-notes --version >/dev/null; then
  echo "course-notes: installed entrypoint is unavailable" >&2
  exit 1
fi
echo "course-notes: installation complete"
