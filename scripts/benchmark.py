#!/usr/bin/env python3
"""Compare two committed sandpile versions sequentially on the same machine."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='origin/main')
    parser.add_argument('--candidate', default='HEAD')
    parser.add_argument('--size', type=int, default=251)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--output', type=Path, default=Path('benchmark-results'))
    args = parser.parse_args()
    if not 1 <= args.size <= 1001 or not 1 <= args.rounds <= 10:
        parser.error('size must be 1..1001 and rounds must be 1..10')

    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    refs = {}
    for label, ref in [('baseline', args.baseline), ('candidate', args.candidate)]:
        if ref.startswith('-'):
            parser.error('refs must not begin with a dash')
        refs[label] = subprocess.check_output(
            ['git', 'rev-parse', '--verify', ref + '^{commit}'], cwd=repo,
            text=True).strip()

    metadata = {
        'refs': refs, 'size': args.size, 'rounds': args.rounds,
        'platform': platform.platform(), 'hostname': platform.node(),
        'compiler': subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0],
        'flags': ['-O3', '-g', '-Werror', '-lm'],
        'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
    }
    cpuinfo = Path('/proc/cpuinfo')
    if cpuinfo.exists():
        metadata['cpu_model'] = next((line.split(':', 1)[1].strip()
            for line in cpuinfo.read_text().splitlines()
            if line.startswith('model name')), 'unknown')
    (output / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')

    with tempfile.TemporaryDirectory(prefix='hw3-benchmark-') as temp:
        builds = {}
        for label, sha in refs.items():
            work = Path(temp) / label
            work.mkdir()
            for filename in ['sandpile.c', 'stb_image_write.h']:
                source = subprocess.check_output(['git', 'show', sha + ':' + filename], cwd=repo)
                (work / filename).write_bytes(source)
            subprocess.run(['gcc', '-O3', '-g', '-Werror', 'sandpile.c',
                            '-lm', '-o', 'sandpile.exe'], cwd=work, check=True)
            builds[label] = work

        def run(label, size):
            work = builds[label]
            start = time.perf_counter()
            subprocess.run([str(work / 'sandpile.exe'), str(size)],
                           cwd=work, stdout=subprocess.DEVNULL, check=True,
                           timeout=3600)
            elapsed = time.perf_counter() - start
            return elapsed, (work / 'identity.png').read_bytes()

        for size in [1, 2, 3, 4, 5, 16, 31, 64]:
            assert run('baseline', size)[1] == run('candidate', size)[1], \
                f'Correctness mismatch at N={size}'
        print('Small-grid PNG comparisons passed.', flush=True)

        samples = []
        with (output / 'samples.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['round', 'version', 'seconds', 'png_sha256'])
            writer.writeheader()
            for iteration in range(args.rounds):
                images = {}
                order = ['baseline', 'candidate'] if iteration % 2 == 0 else ['candidate', 'baseline']
                for label in order:
                    elapsed, image = run(label, args.size)
                    images[label] = image
                    sample = {'round': iteration + 1, 'version': label,
                              'seconds': elapsed, 'png_sha256': hashlib.sha256(image).hexdigest()}
                    writer.writerow(sample)
                    handle.flush()
                    samples.append(sample)
                    print(f'Round {iteration+1}: {label} {elapsed:.4f} s', flush=True)
                assert images['baseline'] == images['candidate'], \
                    f'PNG mismatch at N={args.size}, round {iteration+1}'
            (output / 'identity.png').write_bytes(images['candidate'])

    medians = {label: statistics.median(s['seconds'] for s in samples if s['version'] == label)
               for label in refs}
    speedup = medians['baseline'] / medians['candidate']
    summary = ('## Performance comparison\n\n'
               '| Benchmark | main | PR branch | Speedup |\n'
               '|---|---:|---:|---:|\n'
               f'| Pacman {args.size} x {args.size} | '
               f'{medians["baseline"]:.3f} s | {medians["candidate"]:.3f} s | '
               f'**{speedup:.2f}x** |\n\n'
               f'Times are medians of {args.rounds} sequential runs per version, '
               'with alternating run order. Speedup = main / PR branch; '
               'below 1x means slower. Every measured PNG exactly matches main.\n\n'
               f'Baseline main: `{refs["baseline"]}`.\n\n'
               f'Candidate: `{refs["candidate"]}`.\n\n'
               f'Machine: `{metadata["hostname"]}`. Compiler: `{metadata["compiler"]}`.\n')
    (output / 'summary.md').write_text(summary)
    print(summary)


if __name__ == '__main__':
    main()
