# Run with Docker

Build the image and enter the container from the repository root:

```bash
docker build -t 598ape-weihang-mp3 -f docker/Dockerfile docker
docker run --rm -it -v "$PWD:/workspace" -w /workspace 598ape-weihang-mp3 bash
```

Inside the container:

```bash
git config --global --add safe.directory /workspace
```

## Test an optimization

Run both commits in the table. For example, to test row bounds:

```bash
git checkout 15fe837
gcc -O3 -g -Werror sandpile.c -lm -o sandpile.exe
time ./sandpile.exe 1001
cp identity.png /tmp/before.png

git checkout 196cb4e
gcc -O3 -g -Werror sandpile.c -lm -o sandpile.exe
time ./sandpile.exe 1001
cmp /tmp/before.png identity.png
```

Use the `real` time. Speedup is Before / After. `cmp` prints nothing if the
images match. Each version is run once.

| Change | Before | After |
|---|---|---|
| Queue | `15fe837` | `1f1dc8a` |
| Row bounds | `15fe837` | `196cb4e` |
| Batched toppling | `15fe837` | `4906acc` |
| Mirroring, added to row bounds + batching | `d6ffed5` | `73a1067` |
| Static grid, added to mirroring | `73a1067` | `ddfb1c7` |

GCC is 15.2.0. Keep the machine idle while testing. Times may differ from the
school VM. After testing, run `git checkout main` to return to the final version.
