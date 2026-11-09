# School VM benchmark

Use the repository runner registered to `WeihangLong/598APE-HW3`, with labels
`self-hosted`, `Linux`, and `598ape-hw3`. On the school VM, leave
`~/actions-runner-hw3/run.sh` running in tmux or as a service.

Open **Actions > School VM benchmark > Run workflow**, using the workflow from
`main`. Select a candidate and size `1001`. Each candidate is timed once by
default. Main now contains row bounds, batched toppling, and mirroring. The
workflow has no automatic main-push benchmarks; integrating a feature does not
silently remeasure every old experiment against a changed reference.
Non-draft, same-repository PRs can still trigger comparisons.

The default reference is the version each experiment started from:

| Candidate | Reference |
|---|---|
| Queue | Original baseline `15fe837` |
| Final main (includes mirroring) | Combined row bounds and batching `d6ffed5` |
| Static grid | Dynamic-grid mirror version `73a1067` |

The manual `baseline` input can override this with an exact commit or ref.
Merged optimization branches have been deleted. Their measured commits remain
in main's history; use the commit IDs in `docker/README.md` for those tests.
The queue and static-grid experiment branches remain available. The old
combined-scan branch was deleted after its two features were merged separately;
its source is still available at `d6ffed5`.

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
Only matching output produces a speedup report. Main contains the three successful optimizations; original experiment
branches stay separate. The original baseline is still available at `15fe837`.

Local example after fetching the branches:

```bash
python3 scripts/benchmark.py --baseline 15fe837 \
  --candidate 196cb4e --size 31 --rounds 1 \
  --baseline-cache-dir /tmp/hw3-baseline-cache --output /tmp/hw3-results
```
