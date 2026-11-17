"""Solve exported Unity bottle data with capacities, receivers and one-source-per-lock rules."""
import collections, heapq, itertools, json, time
from pathlib import Path

class Puzzle:

    def __init__(self, level):
        self.level = level['level']
        self.special = level['special']
        self.bs = level['bottles']
        self.n = len(self.bs)
        self.caps = tuple((b['capacity'] for b in self.bs))
        self.initial = tuple((tuple((c for c in b['colors'] if c and c != 'Empty')) for b in self.bs))
        self.receiver = tuple((b['fixedReceiver'] for b in self.bs))
        self.goals = tuple((b['receiverColor'] for b in self.bs))
        self.locks = tuple((b['lockEnabled'] for b in self.bs))
        self.unlock = tuple((b['unlockColor'] or '' for b in self.bs))
        self.exempt = tuple((b['noLockColor'] or '' for b in self.bs))
        self.haslocks = any(self.locks)
        self.units = sum(map(len, self.initial))
        self.expected = self.units // 4
        self.groups = {}
        for (i, b) in enumerate(self.bs):
            key = (self.caps[i], self.receiver[i], self.goals[i] if self.receiver[i] else '')
            self.groups.setdefault(key, []).append(i)

    def full(self, s, i):
        return len(s[i]) == self.caps[i] and len(set(s[i])) == 1

    def needs(self, s, i):
        return self.locks[i] and self.exempt[i] not in s[i]

    def assignments(self, s, old):
        assigned = list(old)

        def valid(i, j):
            return i != j and self.full(s, j) and (not self.needs(s, j) or assigned[j] >= 0) and (not self.unlock[i] or s[j][-1] == self.unlock[i])
        changed = True
        while changed:
            changed = False
            for (i, j) in enumerate(assigned):
                if j >= 0 and (not self.needs(s, i) or not valid(i, j)):
                    assigned[i] = -1
                    changed = True
        claimed = set((j for j in assigned if j >= 0))
        for j in range(self.n):
            if j in claimed:
                continue
            for i in range(self.n):
                if self.needs(s, i) and assigned[i] < 0 and valid(i, j):
                    assigned[i] = j
                    claimed.add(j)
                    break
        return tuple(assigned)

    def locked(self, s, a, i):
        return self.needs(s, i) and a[i] < 0

    def won(self, s):
        if self.special:
            return any((self.receiver[i] and self.full(s, i) and (s[i][-1] == self.goals[i]) for i in range(self.n)))
        return all((not stack or self.full(s, i) for (i, stack) in enumerate(s)))

    def key(self, s, a):
        if self.haslocks:
            return (s, a)
        return tuple((tuple(sorted((s[i] for i in ids))) for ids in self.groups.values()))

    def heuristic(self, s, a):
        if self.special:
            goal = next((i for i in range(self.n) if self.receiver[i]))
            color = self.goals[goal]
            buried = sum((sum((1 for c in stack[k + 1:] if c != color)) for stack in s for (k, c) in enumerate(stack) if c == color))
            return self.caps[goal] - len(s[goal]) + buried * 0.6
        segments = sum((1 + sum((x != y for (x, y) in zip(stack, stack[1:]))) for stack in s if stack))
        return segments - self.expected + sum((self.locked(s, a, i) for i in range(self.n))) * 1.5

    def moves(self, s, a):
        for (i, stack) in enumerate(s):
            if not stack or self.receiver[i] or self.locked(s, a, i):
                continue
            if self.full(s, i) and self.exempt[i] not in stack:
                continue
            c = stack[-1]
            run = 1
            while run < len(stack) and stack[-run - 1] == c:
                run += 1
            seen_targets = set()
            for (j, target) in enumerate(s):
                if i == j or len(target) >= self.caps[j] or self.locked(s, a, j):
                    continue
                if self.receiver[j]:
                    if c != self.goals[j] or any((x != c for x in target)):
                        continue
                elif target and target[-1] != c:
                    continue
                if not self.haslocks:
                    equivalent = (target, self.receiver[j], self.caps[j], self.goals[j] if self.receiver[j] else '')
                    if equivalent in seen_targets:
                        continue
                    seen_targets.add(equivalent)
                    if not target and run == len(stack) and (not self.receiver[j]):
                        continue
                count = min(run, self.caps[j] - len(target))
                new = list(s)
                new[i] = stack[:-count]
                new[j] = target + (c,) * count
                new = tuple(new)
                na = self.assignments(new, a) if self.haslocks else a
                yield ((i, j, count), new, na)

    def solve(self, max_nodes=500000, seconds=20):
        start = time.monotonic()
        a = self.assignments(self.initial, (-1,) * self.n)
        counter = itertools.count()
        initial = (self.initial, a)
        parents = {initial: None}
        distance = {self.key(*initial): 0}
        queue = [(self.heuristic(*initial) * 3, 0, next(counter), initial)]
        expanded = 0
        while queue:
            (_, depth, _, node) = heapq.heappop(queue)
            (s, a) = node
            if self.won(s):
                solution = []
                while parents[node] is not None:
                    (prev, move) = parents[node]
                    solution.append(move)
                    node = prev
                return dict(status='solved', moves=list(reversed(solution)), expanded=expanded, seconds=round(time.monotonic() - start, 3))
            if depth > distance.get(self.key(s, a), depth):
                continue
            expanded += 1
            if expanded > max_nodes or time.monotonic() - start > seconds:
                return dict(status='search_limit', expanded=expanded, seconds=round(time.monotonic() - start, 3))
            for (move, ns, na) in self.moves(s, a):
                nextnode = (ns, na)
                key = self.key(ns, na)
                nd = depth + 1
                if nd >= distance.get(key, 10 ** 9):
                    continue
                distance[key] = nd
                parents[nextnode] = ((s, a), move)
                heapq.heappush(queue, (nd + self.heuristic(ns, na) * 3, nd, next(counter), nextnode))
        return dict(status='unsolvable', expanded=expanded, seconds=round(time.monotonic() - start, 3))

    def replay(self, moves):
        s = self.initial
        a = self.assignments(s, (-1,) * self.n)
        for move in moves:
            choices = {tuple(m): (ns, na) for (m, ns, na) in self.moves(s, a)}
            if tuple(move) not in choices:
                raise ValueError((self.level, 'illegal move', move))
            (s, a) = choices[tuple(move)]
        if not self.won(s):
            raise ValueError((self.level, 'solution does not win'))
        return s
