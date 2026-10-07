#!/usr/bin/env bash
# Verify every committed submodule pointer is published on its remote.
# Run before pushing ansible main and before Semaphore deploys: a bumped
# but unpushed pointer passes local git, then kills every Semaphore task
# with "upload-pack: not our ref" at clone time.
# Usage: scripts/check-submodules.sh [repo-root]
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

fail=0
# git ls-files -s format: "<mode> <sha> <stage>\t<path>" — default IFS covers both separators
while read -r mode sha1 _stage path; do
    [ "$mode" = "160000" ] || continue
    (
        cd "$path" || exit 1
        if ! git fetch -q origin --prune 2>/dev/null; then
            echo "FAIL $path: git fetch origin failed"
            exit 1
        fi
        if branch=$(git branch -r --contains "$sha1" 2>/dev/null) && [ -n "$branch" ]; then
            echo "ok   $path @ ${sha1:0:7} ($(echo "$branch" | head -1 | xargs))"
        else
            echo "FAIL $path @ ${sha1:0:7}: commit is on no remote branch — push the submodule first: git -C $path push origin HEAD:\$(git -C $path branch --show-current)"
            exit 1
        fi
    ) || fail=1
done < <(git ls-files -s)

if [ "$fail" -ne 0 ]; then
    echo "submodule check FAILED — deploy would break, push the submodules listed above"
fi
exit "$fail"
