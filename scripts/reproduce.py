#!/usr/bin/env python3
"""Build fixed experiment commits, check their PNGs, and time each version once."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time


VERSIONS = {
    'baseline': '15fe837445b8e32a15ac61fcfa388980b54d9173',
    'row-bounds': '196cb4e22dc49034d44587e80e6ecfba20de9e86',
    'batch': '4906acc75caf5d721cf3258cf7852d865d209be1',
    'combined': 'd6ffed56b4a8fe45bd5c74d69028f46dba9d5a6c',
    'mirror': '73a10677459c3d641bed59aee4cf6972b404fc7b',
    'queue': '1f1dc8a487d526a1068d62171bc57318256f63dc',
    'static': 'ddfb1c7e86931587f222d5e7b5f05dadd3b948bb',
}
COMPARISONS = {
    'queue': ('baseline', 'queue'),
    'row-bounds': ('baseline', 'row-bounds'),
    'batch': ('baseline', 'batch'),
    'mirror': ('combined', 'mirror'),
    'static': ('mirror', 'static'),
    'combined': ('baseline', 'combined'),
}
DEFAULTS = ['queue', 'row-bounds', 'batch', 'mirror', 'static']
FLAGS = ['-O3', '-g', '-Werror', '-lm']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiments', nargs='+', choices=['all', *COMPARISONS], default=['all'])
    parser.add_argument('--size', type=int, default=1001)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--output', type=Path, default=Path('reproduction-results'))
    args = parser.parse_args()
    if not 1 <= args.size <= 1001 or not 1 <= args.rounds <= 10:
        parser.error('size must be 1..1001 and rounds must be 1..10')
    experiments = list(dict.fromkeys(DEFAULTS if 'all' in args.experiments else args.experiments))
    pairs = {name: COMPARISONS[name] for name in experiments}
    needed = {version for pair in pairs.values() for version in pair}
    versions = {name: sha for name, sha in VERSIONS.items() if name in needed}
    if {'baseline', 'mirror'} <= needed:
        pairs['overall'] = ('baseline', 'mirror')

    repo = Path(__file__).resolve().parents[1]
    for sha in versions.values():
        probe = subprocess.run(['git', 'cat-file', '-e', sha + '^{commit}'], cwd=repo,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode:
            parser.error(f'missing commit {sha}; fetch the full repository history first')
    args.output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = Path(tempfile.mkdtemp(prefix=f'hw3-{stamp}-', dir=args.output.resolve()))
    print(f'Results: {output}', flush=True)
    metadata = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'size': args.size, 'rounds': args.rounds, 'versions': versions,
        'comparisons': pairs, 'flags': FLAGS,
        'compiler': subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0],
        'platform': platform.platform(), 'architecture': platform.machine(),
        'python': platform.python_version(), 'cpu_count': os.cpu_count(),
        'hostname': platform.node(),
        'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
    }
    cpuinfo = Path('/proc/cpuinfo')
    if cpuinfo.exists():
        metadata['cpu_model'] = next((line.split(':', 1)[1].strip()
            for line in cpuinfo.read_text().splitlines() if line.startswith('model name')), 'unknown')
    (output / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')

    builds = {}
    for name, sha in versions.items():
        work = output / name
        work.mkdir()
        for filename in ['sandpile.c', 'stb_image_write.h']:
            source = subprocess.check_output(['git', 'show', sha + ':' + filename], cwd=repo)
            (work / filename).write_bytes(source)
        with (work / 'build.log').open('w') as log:
            subprocess.run(['gcc', '-O3', '-g', '-Werror', 'sandpile.c', '-lm', '-o', 'sandpile.exe'],
                           cwd=work, stdout=log, stderr=log, check=True)
        builds[name] = work
        print(f'Built {name}: {sha[:12]}', flush=True)

    def run(name, size, log):
        work = builds[name]
        start = time.perf_counter()
        subprocess.run([str(work / 'sandpile.exe'), str(size)], cwd=work,
                       stdout=log, stderr=log, check=True, timeout=3600)
        elapsed = time.perf_counter() - start
        return elapsed, (work / 'identity.png').read_bytes()

    for size in [1, 2, 3, 4, 5, 16, 31, 64]:
        reference = None
        for name in versions:
            image = run(name, size, subprocess.DEVNULL)[1]
            if reference is None:
                reference = image
            if image != reference:
                raise RuntimeError(f'PNG mismatch for {name} at N={size}')
    print('Small-grid PNG comparisons passed.', flush=True)

    samples = []
    with (output / 'samples.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['round', 'version', 'commit', 'seconds', 'png_sha256'])
        writer.writeheader()
        for iteration in range(args.rounds):
            order = list(versions) if iteration % 2 == 0 else list(reversed(versions))
            reference = None
            for name in order:
                print(f'Round {iteration+1}: running {name}, N={args.size} ...', flush=True)
                with (builds[name] / f'run-{iteration+1}.log').open('w') as log:
                    elapsed, image = run(name, args.size, log)
                sample = {'round': iteration + 1, 'version': name, 'commit': versions[name],
                          'seconds': elapsed, 'png_sha256': hashlib.sha256(image).hexdigest()}
                writer.writerow(sample)
                handle.flush()
                samples.append(sample)
                if reference is None:
                    reference = image
                if image != reference:
                    raise RuntimeError(f'PNG mismatch for {name} at N={args.size}, round {iteration+1}')
                print(f'{name}: {elapsed:.3f} s; PNG matches', flush=True)

    times = {name: statistics.median(s['seconds'] for s in samples if s['version'] == name)
             for name in versions}
    rows = []
    for experiment, (before, after) in pairs.items():
        rows.append({'experiment': experiment, 'before': before, 'after': after,
                     'before_seconds': times[before], 'after_seconds': times[after],
                     'speedup': times[before] / times[after]})
    with (output / 'comparisons.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = ['# Performance comparison', '',
               '| Experiment | Reference | Candidate | Before | After | Speedup |',
               '|---|---|---|---:|---:|---:|']
    for row in rows:
        summary.append(f'| {row["experiment"]} | {row["before"]} | {row["after"]} | '
                       f'{row["before_seconds"]:.3f} s | {row["after_seconds"]:.3f} s | '
                       f'{row["speedup"]:.2f}x |')
    summary += ['', f'N={args.size}; {args.rounds} timed run(s) per unique version. '
                + ('Times are single measurements.' if args.rounds == 1 else 'Times are medians.'),
                'A shared version is measured once per round and reused in every comparison that needs it.',
                'Every measured PNG matches. Compilation and PNG comparison are outside the timer.',
                f'Compiler: {metadata["compiler"]}.',
                'Exact commits and machine details are in environment.json.', '']
    (output / 'summary.md').write_text('\n'.join(summary))
    print('\n'.join(summary), flush=True)


if __name__ == '__main__':
    main()
