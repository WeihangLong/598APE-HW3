# School VM runner setup

This configuration keeps the repository under `WeihangLong/598APE-HW3`.
It registers a repository-level runner instead of trying to reuse the
organization-scoped `Ringo-Leo` runner group `598ape`.

1. Log in to your school VM. It needs Git, GCC, Python 3, and the GitHub
   runner's system dependencies. Use a separate runner directory such as
   `~/actions-runner-hw3`; do not reconfigure the HW2 runner.
2. In the HW3 repository, open **Settings > Actions > Runners > New
   self-hosted runner**. Choose the VM's operating system and architecture.
3. Execute GitHub's current download and configuration commands on that VM.
   Keep the registration token private. When asked for additional labels,
   enter `598ape-hw3`. Name the runner `598ape-hw3` if desired.
4. Run `./run.sh` on the VM and leave it active in a terminal multiplexer,
   or install the runner as a service using GitHub's service instructions.
   Confirm the runner appears **Idle** in the repository's runner settings.
5. Review and merge this CI-only change into `main` to make manual
   `workflow_dispatch` runs available. This adds infrastructure files only;
   `sandpile.c` remains the instructor baseline. The three optimization
   branches do not need to be merged. Preserve their PRs for comparison.
6. Open **Actions > School VM benchmark > Run workflow**, choose one of the
   three optimization branches, set size to `1001` and rounds to `3`.
   Read the automatic performance comment on that branch's open PR. Repeated
   runs update the existing bot comment. Results also appear in the job summary;
   download raw samples, machine/compiler metadata, and the checked PNG from
   the artifact. No additional GitHub token is needed.

Merging the CI configuration into main also triggers sequential comparisons
of all three experiment branches, posting each result to its respective PR.
Later pushes to main that change benchmark infrastructure or source repeat
these comparisons. The matrix is serial, and artifacts are separate per version.

Optimization PR checks and manual comparisons default to size `1001` and three
runs per version. The CI-only PR uses size `251` to validate infrastructure.
Repository variables `HW3_GRID_SIZE` and `HW3_ROUNDS` can override defaults;
explicit manual inputs take precedence. Baseline and candidate use the same GCC flags
and execute sequentially on the same runner, alternating run order. Keep the
machine otherwise idle; this workflow's concurrency only serializes jobs
from this repository, not other users' workloads.

The benchmark script compiles committed sources into temporary directories.
It does not overwrite the runner's working source, and compilation is outside
the timed interval. A run fails if the full PNG differs from the baseline.

The reference is always `origin/main` as fetched for the run, not `HEAD^`.
The comment records both exact commit IDs, and reports main-time / PR-time.
Only matching output produces a speedup report. If a new commit arrives during
measurement, the older run does not overwrite the latest PR results.

Local smoke test after fetching the optimization branches:

```bash
python3 scripts/benchmark.py --baseline origin/main \
  --candidate origin/optimize/mirror-scan-bulk --size 31 --rounds 1
```
