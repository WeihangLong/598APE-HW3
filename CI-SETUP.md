# School VM benchmark

Use the repository runner registered to `WeihangLong/598APE-HW3`, with labels
`self-hosted`, `Linux`, and `598ape-hw3`. On the school VM, leave
`~/actions-runner-hw3/run.sh` running in tmux or as a service.

Open **Actions > School VM benchmark > Run workflow**, using the workflow from
`main`. Choose a candidate branch and size `1001`. Each version is timed once by
default. A push to main that changes the benchmark or source automatically runs
`optimize/row-bounds` and `optimize/batched-toppling` sequentially. Non-draft,
same-repository PRs also trigger their own comparison. Draft PRs skip benchmarks.
The original combined scan, mirror, queue, and static-grid branches are preserved;
choose them manually when needed. New main deployments supersede older runs.

## Reusing the baseline

For single-round jobs, the runner keeps the baseline time and its complete PNG
in `$RUNNER_TOOL_CACHE/hw3-baselines`. The first comparison measures the baseline
once; later comparisons reuse it if the baseline source files, grid size,
compiler version, flags, OS, hostname, CPU model, and CPU affinity match.
Infrastructure-only commits therefore do not force another baseline run.
Each candidate is still measured once and compared byte-for-byte with the
baseline image. Cheap small-grid comparisons are still run for correctness.
A lock prevents local invocations sharing this cache from overlapping.

The bot comment says whether the baseline was reused and records its original
measurement time, source commit, and CI run URL. Raw CSV rows include a `reused`
field. An earlier cached time is not a fresh paired measurement; changing VM
load can affect the speedup. Keep the VM otherwise idle. To force a fresh
single-run reference, remove the runner's `hw3-baselines` directory while no
benchmark is running. Multiple-round manual jobs bypass the baseline cache and
alternate baseline/candidate runs. The default is one round, regardless of the
old `HW3_ROUNDS` repository variable.

Results appear in the job summary and update the matching open PR's bot comment.
The artifact includes raw samples, metadata, and the checked candidate PNG.
The comment records both exact commit IDs and skips stale PR heads.
Compilation and PNG comparison are outside the timed interval. All builds use
`gcc -O3 -g -Werror sandpile.c -lm -o sandpile.exe` in temporary directories.
Only matching output produces a speedup report. Main's computation remains the
instructor baseline; optimization branches stay separate.

Local example after fetching the branches:

```bash
python3 scripts/benchmark.py --baseline origin/main \
  --candidate origin/optimize/row-bounds --size 31 --rounds 1 \
  --baseline-cache-dir /tmp/hw3-baseline-cache --output /tmp/hw3-results
```
