#!/usr/bin/env python3
"""Table of a MISTER_PROF sample file (backends/platform/sdl/mister/mister-prof.cpp).
usage: tools/prof.py <syms.txt> <prof.bin> [<earlier prof.bin>] [-n rows] [-c]
  syms.txt     arm-linux-gnueabihf-nm -C --defined-only -n build/mister/scummvm
  earlier      a dump of the same run taken before: only the samples after it
  -c           count a sample for its caller (return address) too, as "callers" """
import bisect, collections, struct, sys

args = [a for a in sys.argv[1:] if not a.startswith('-')]
rows = 40
if '-n' in sys.argv:
    rows = int(sys.argv[sys.argv.index('-n') + 1])
    args.remove(str(rows))
callers = '-c' in sys.argv

addrs, names = [], []
for line in open(args[0]):
    parts = line.rstrip('\n').split(' ', 2)
    if len(parts) < 3 or parts[1] not in 'tTwW':
        continue
    addrs.append(int(parts[0], 16))
    names.append(parts[2])

def name(pc):
    i = bisect.bisect_right(addrs, pc) - 1
    return names[i] if i >= 0 else '?'

data = open(args[1], 'rb').read()
skip = len(open(args[2], 'rb').read()) // 12 if len(args) > 2 else 0
samples = [struct.unpack_from('<III', data, i * 12) for i in range(skip, len(data) // 12)]
print(f'{len(samples)} samples')

threads = collections.Counter(s[0] for s in samples)
for tid, n in threads.most_common():
    print(f'thread {tid}: {n} ({100 * n / len(samples):.1f}%)')

for tid, n in threads.most_common(3):
    print(f'\n== thread {tid}')
    funcs = collections.Counter(name(s[1]) for s in samples if s[0] == tid)
    for f, c in funcs.most_common(rows):
        print(f'{100 * c / n:5.1f}%  {f[:150]}')
    if callers:
        pairs = collections.Counter((name(s[1]), name(s[2])) for s in samples if s[0] == tid)
        print('-- with callers')
        for (f, c2), c in pairs.most_common(rows):
            print(f'{100 * c / n:5.1f}%  {f[:70]}  <-  {c2[:70]}')
