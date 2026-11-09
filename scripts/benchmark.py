#!/usr/bin/env python3
"""Compare committed sandpile versions, optionally reusing a runner-local baseline."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time


FLAGS = ['-O3', '-g', '-Werror', '-lm']
FILES = ['sandpile.c', 'stb_image_write.h']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='origin/main')
    parser.add_argument('--candidate', default='HEAD')
    parser.add_argument('--size', type=int, default=1001)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--baseline-cache-dir', type=Path)
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
        'flags': FLAGS,
        'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
    }
    cpuinfo = Path('/proc/cpuinfo')
    if cpuinfo.exists():
        metadata['cpu_model'] = next((line.split(':', 1)[1].strip()
            for line in cpuinfo.read_text().splitlines()
            if line.startswith('model name')), 'unknown')
    baseline_blobs = {name: subprocess.check_output(
        ['git', 'rev-parse', refs['baseline'] + ':' + name], cwd=repo,
        text=True).strip() for name in FILES}
    cache_inputs = {key: value for key, value in metadata.items() if key not in ('refs', 'rounds')}
    cache_inputs.update(schema=1, baseline_blobs=baseline_blobs)
    key = hashlib.sha256(json.dumps(cache_inputs, sort_keys=True).encode()).hexdigest()
    cache = None
    if args.baseline_cache_dir and args.rounds == 1:
        root = args.baseline_cache_dir.resolve()
        root.mkdir(parents=True, exist_ok=True)
        # Also serialize local invocations sharing this cache on the runner.
        lock = (root / 'benchmark.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX)
        cache = root / key
        cache.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='hw3-benchmark-') as temp:
        builds = {}
        for label, sha in refs.items():
            work = Path(temp) / label
            work.mkdir()
            for filename in FILES:
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
            if run('baseline', size)[1] != run('candidate', size)[1]:
                raise RuntimeError(f'Correctness mismatch at N={size}')
        print('Small-grid PNG comparisons passed.', flush=True)

        cached = None
        if cache and (cache / 'result.json').exists():
            try:
                saved = json.loads((cache / 'result.json').read_text())
                image = (cache / 'identity.png').read_bytes()
                if (saved['inputs'] == cache_inputs
                        and hashlib.sha256(image).hexdigest() == saved['png_sha256']
                        and math.isfinite(saved['seconds']) and saved['seconds'] > 0):
                    cached = saved, image
            except (OSError, ValueError, KeyError, TypeError):
                pass
            if cached is None:
                print('Baseline cache invalid; measuring again.', flush=True)

        samples = []
        with (output / 'samples.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'round', 'version', 'seconds', 'png_sha256', 'reused'])
            writer.writeheader()
            for iteration in range(args.rounds):
                images = {}
                order = ['baseline', 'candidate'] if iteration % 2 == 0 else ['candidate', 'baseline']
                for label in order:
                    reused = label == 'baseline' and cached is not None
                    if reused:
                        saved, image = cached
                        elapsed = saved['seconds']
                        print(f'Reusing baseline measured at {saved["measured_at"]}.', flush=True)
                    else:
                        print(f'Round {iteration+1}: running {label}, N={args.size} ...', flush=True)
                        elapsed, image = run(label, args.size)
                    images[label] = image
                    sample = {'round': iteration + 1, 'version': label,
                              'seconds': elapsed, 'png_sha256': hashlib.sha256(image).hexdigest(),
                              'reused': reused}
                    writer.writerow(sample)
                    handle.flush()
                    samples.append(sample)
                    if label == 'baseline' and args.rounds == 1:
                        if not reused:
                            saved = {'inputs': cache_inputs, 'seconds': elapsed,
                                     'png_sha256': sample['png_sha256'],
                                     'commit': refs['baseline'],
                                     'measured_at': datetime.now(timezone.utc).isoformat(),
                                     'run_url': os.environ.get('BENCHMARK_RUN_URL')}
                            if cache:
                                # Publish JSON last, so an interrupted write cannot be a valid entry.
                                (cache / 'identity.png').write_bytes(image)
                                staging = cache / 'result.tmp.json'
                                staging.write_text(json.dumps(saved, indent=2) + '\n')
                                staging.replace(cache / 'result.json')
                        metadata['baseline_measurement'] = dict(saved, reused=reused, cache_key=key)
                    print(f'Round {iteration+1}: {label} {elapsed:.4f} s (reused={reused})', flush=True)
                if images['baseline'] != images['candidate']:
                    raise RuntimeError(f'PNG mismatch at N={args.size}, round {iteration+1}')
            (output / 'identity.png').write_bytes(images['candidate'])

    (output / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')
    medians = {label: statistics.median(s['seconds'] for s in samples if s['version'] == label)
               for label in refs}
    speedup = medians['baseline'] / medians['candidate']
    if args.rounds == 1:
        measurement = metadata['baseline_measurement']
        timing_note = ('Candidate was timed once. Baseline was '
                       + ('reused from the runner-local cache' if measurement['reused'] else 'timed once in this job')
                       + f' (measured {measurement["measured_at"]}, source commit `{measurement["commit"]}`). '
                       'Only matching baseline source files, size, compiler, flags, machine, and CPU affinity reuse a result. '
                       'A cached time is an earlier measurement, not a new paired run.\n\n')
        if measurement.get('run_url'):
            timing_note += f'[Baseline measurement run]({measurement["run_url"]})\n\n'
    else:
        timing_note = (f'Times are medians of {args.rounds} sequential runs per version, '
                       'with alternating run order. Baseline caching is disabled for multiple rounds.\n\n')
    summary = ('## Performance comparison\n\n'
               '| Benchmark | main | PR branch | Speedup |\n'
               '|---|---:|---:|---:|\n'
               f'| Pacman {args.size} x {args.size} | '
               f'{medians["baseline"]:.3f} s | {medians["candidate"]:.3f} s | '
               f'**{speedup:.2f}x** |\n\n'
               + timing_note + 'Speedup = main / PR branch; below 1x means slower. '
               'Every measured candidate PNG exactly matches the baseline PNG.\n\n'
               f'Baseline main: `{refs["baseline"]}`.\n\n'
               f'Candidate: `{refs["candidate"]}`.\n\n'
               f'Machine: `{metadata["hostname"]}`. Compiler: `{metadata["compiler"]}`.\n')
    (output / 'summary.md').write_text(summary)
    print(summary)


if __name__ == '__main__':
    main()
