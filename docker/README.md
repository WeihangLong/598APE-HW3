# Reproduce the HW3 experiments

The Docker image provides GCC 15.2.0, Python 3, and Git. The GCC base image is
pinned by digest. Programs use `gcc -O3 -g -Werror sandpile.c -lm -o sandpile.exe`.
This matches the compiler version and flags used on the school VM, but Docker
does not reproduce that VM's CPU, load, or Ubuntu compiler build. Your times
and speedups may differ.

## Get the code

Install Docker and Git. Clone this private repository using an account with
access. Keep the full Git history; the script reads the experiment commits.

```bash
git clone git@github.com:WeihangLong/598APE-HW3.git
cd 598APE-HW3
git fetch origin
```

For an existing shallow clone, run `git fetch --unshallow origin` first.
Run the commands below from the repository root.

## Build the image

```bash
./dockerbuild.sh
```

Or use Docker directly:

```bash
docker build -t 598ape-weihang-mp3 -f docker/Dockerfile docker
```

Only the small `docker` directory is sent as the build context. Source code
and Git credentials are not copied into the image. The run helper mounts the
repository and Git metadata read-only, and writes results to a separate folder.

## Check the setup first

```bash
./dockerrun.sh --size 31
```

This builds all seven versions and compares their output on small odd and even
grids. It then times each version once at N=31. These small timings are only a
setup check; the homework benchmark is N=1001.

## Run all five experiments

```bash
./dockerrun.sh --size 1001
```

The script runs programs sequentially, with one timed run per unique version.
It measures the full program, including allocation, computation, and PNG output.
Compilation and PNG comparison are outside the timer. If several experiments
use the same reference, its time is measured once and reused within this run.
The mirror version is also measured only once, even though it is both a
candidate and the reference for the static-grid experiment. Old result folders
are not used as a timing cache.

The queue version is slow. The full command can take around an hour or longer,
depending on the machine. Keep the machine idle and avoid running benchmarks
in parallel. Docker needs network access while building the image; the
benchmark itself reads local Git objects and does not need network access.

## Run selected experiments

```bash
./dockerrun.sh --experiments row-bounds batch --size 1001
./dockerrun.sh --experiments mirror --size 1001
./dockerrun.sh --experiments static --size 1001
./dockerrun.sh --experiments queue --size 1001
./dockerrun.sh --experiments combined --size 1001
```

Only the versions needed by the selected comparisons are built and timed.
Add `--rounds 3` for three runs per version. The default is one run; multiple
rounds reverse the version order every other round and report median times.

## Versions and references

| Experiment | Before | After |
|---|---|---|
| Queue | Original baseline | FIFO queue with batching |
| Row bounds | Original baseline | Row bounds only |
| Batch | Original baseline | Batched toppling only |
| Mirror | Row bounds + batching | Same version + mirroring |
| Static | Dynamic-grid mirror | Same version with a static grid |
| Combined (optional) | Original baseline | Row bounds + batching |

The source commits are fixed in `scripts/reproduce.py`:

| Version | Commit |
|---|---|
| Original baseline | `15fe837445b8e32a15ac61fcfa388980b54d9173` |
| Row bounds only | `196cb4e22dc49034d44587e80e6ecfba20de9e86` |
| Batch only | `4906acc75caf5d721cf3258cf7852d865d209be1` |
| Row bounds + batching | `d6ffed56b4a8fe45bd5c74d69028f46dba9d5a6c` |
| Mirror | `73a10677459c3d641bed59aee4cf6972b404fc7b` |
| Queue | `1f1dc8a487d526a1068d62171bc57318256f63dc` |
| Static grid | `ddfb1c7e86931587f222d5e7b5f05dadd3b948bb` |

Main contains the three successful changes. Its `sandpile.c` matches the mirror
source above. The static-grid commit includes current CI infrastructure, but
its computation code is unchanged from the original static experiment.
The script extracts only `sandpile.c` and `stb_image_write.h` from each commit.
It does not check out branches or change the working source.

## Read the results

Each invocation creates a new folder under `reproduction-results/` on the host.
The same folder appears as `/results/` inside the container. It contains:

- `summary.md`: before/after times and speedups, with each reference named.
- `comparisons.csv`: numeric comparison results.
- `samples.csv`: every timed sample, commit, and PNG SHA-256.
- `environment.json`: exact commits, compiler, flags, CPU, and run settings.
- One directory per version with extracted sources, binary, logs, and PNG.

Speedup is before-time / after-time; below 1 means slower. If both original
baseline and mirror were selected, the summary also includes their overall
speedup. Every selected version must produce exactly the same PNG bytes on
N=1,2,3,4,5,16,31,64 and on the requested size. Any mismatch fails the run.
The output images provide an additional visual check against `identity-ref.png`.

To change the image name or output folder:

```bash
./dockerbuild.sh my-hw3-image
HW3_DOCKER_IMAGE=my-hw3-image HW3_RESULTS_DIR="$HOME/hw3-results" \
  ./dockerrun.sh --experiments static --size 1001
```

## Run without Docker

With GCC, Python 3, and Git installed, the same script also works directly:

```bash
python3 scripts/reproduce.py --size 1001 --output reproduction-results
```

This uses the host compiler. Read `environment.json` before comparing it with
the school-VM results. For pairwise CI checks and baseline caching across CI
jobs, see `CI-SETUP.md` and `scripts/benchmark.py`.
