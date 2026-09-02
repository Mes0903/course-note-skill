#!/usr/bin/env bash
set -euo pipefail

COURSE_NOTES_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
COURSE_NOTES_REPO_ROOT="$(cd -- "$COURSE_NOTES_SCRIPT_DIR/.." && pwd -P)"
COURSE_NOTES_DEVICE=auto

course_notes_usage() {
  echo "Usage: scripts/install.sh [--device auto|cuda|cpu]" >&2
}

while (($#)); do
  case "$1" in
    --device)
      (($# >= 2)) || { course_notes_usage; exit 2; }
      COURSE_NOTES_DEVICE="$2"
      shift 2
      ;;
    --help)
      course_notes_usage
      exit 0
      ;;
    *)
      course_notes_usage
      exit 2
      ;;
  esac
done

case "$COURSE_NOTES_DEVICE" in
  auto|cuda|cpu) ;;
  *)
    echo "course-notes: --device must be auto, cuda, or cpu" >&2
    exit 2
    ;;
esac
export COURSE_NOTES_INSTALL_DEVICE="$COURSE_NOTES_DEVICE"
exec "$COURSE_NOTES_SCRIPT_DIR/lib/install-body.sh" "$COURSE_NOTES_REPO_ROOT"
