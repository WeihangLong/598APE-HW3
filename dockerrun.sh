#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
IMAGE=${HW3_DOCKER_IMAGE:-598ape-weihang-mp3}
OUTPUT_DIR=${HW3_RESULTS_DIR:-"$SCRIPT_DIR/reproduction-results"}
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(CDPATH= cd -- "$OUTPUT_DIR" && pwd)
# Mount Git's common directory separately so linked worktrees also work.
GIT_METADATA=$(git -C "$SCRIPT_DIR" rev-parse --path-format=absolute --git-common-dir)

exec docker run --rm \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$SCRIPT_DIR,dst=/workspace,readonly" \
  --mount "type=bind,src=$GIT_METADATA,dst=/git,readonly" \
  --mount "type=bind,src=$OUTPUT_DIR,dst=/results" \
  --env GIT_DIR=/git --env GIT_WORK_TREE=/workspace \
  "$IMAGE" python3 scripts/reproduce.py --output /results "$@"
