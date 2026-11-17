# Water-sort level validator

A dependency-free Python tool extracted from Unity game-development tooling. It checks color inventories, searches for legal solutions, and replays every returned move against the model.

It addresses a practical content bug: a level may look plausible while containing too few units of a color to complete its bottles or special collector.

## Run it

Requires Python 3.9 or later. No packages or Unity installation are needed.

```sh
python3 validate.py levels.json --output report.json
python3 -m unittest -v
```

The checked-in `levels.json` is a sanitized 50-level snapshot containing puzzle rules and color stacks. Normal bottles have capacity four; special collectors occur at levels 10, 20, and 30. Arrays store colors **bottom to top**, with `Empty` representing an unoccupied slot.

## Report states

| State | Meaning |
| --- | --- |
| `invalid_inventory` | A basic content check fails, such as an incomplete four-unit color set or insufficient collector color. |
| `solved` | A move sequence was found and successfully replayed to the modeled win condition. |
| `search_limit` | The node or time budget was exhausted; solvability remains unknown. |
| `unsolvable` | Search exhausted the reachable states in this model without finding a win. |

Exit code `0` means all levels solved; `1` means at least one level is invalid, unresolved, or a dead end; `2` reports an input or command-line error.

```sh
python3 validate.py levels.json --seconds 5 --max-nodes 100000 --output report.json
```

## Rules modeled

- Pour only the contiguous top-color run, limited by destination capacity.
- Pour onto the same color or into an empty ordinary bottle.
- Keep completed ordinary bottles fixed, except where the exported exemption rule permits movement.
- Allow fixed receivers to accept only their goal color and never act as a source.
- Model lock ownership: a completed matching bottle can unlock one locked bottle at a time.
- Win normal levels when every occupied bottle is full and monochrome; win special levels when the goal receiver is full.

## Search design

`solver.py` uses a weighted best-first search (`depth + 3 × heuristic`) with parent pointers and state deduplication. Equivalent unlocked bottles are canonicalized to reduce redundant search. Lock-bearing levels retain bottle identity and assignment state.

The heuristic favors fewer color segments in normal levels and progress toward the collector in special levels. It is a practical solver, **not a shortest-solution guarantee**. State-space growth is exponential in the worst case, so node and time budgets are explicit.

## Tests

The test suite covers insufficient colors, missing unlock colors, capacity errors, collector constraints, illegal moves, immutable input, incomplete searches, dead ends, and solution replay across the full 50-level snapshot.

## Scope

This tool validates a discrete, project-specific logical model. It does not run Unity animations, ad SDKs, UI layouts, hidden-color presentation, or device input. Scene exports must remain consistent with the runtime rules. Changing bottle capacities or lock semantics requires updating the model and its tests.

See the [Unity case study](https://github.com/mobeenafzal570/water-sort-unity-case-study) for the associated gameplay and UI work.

Development and documentation used AI assistance. The runnable tests and explicit model boundaries make the results reviewable.
