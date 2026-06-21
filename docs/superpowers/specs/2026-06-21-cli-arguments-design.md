# CLI Arguments Design

## Goal

Replace the hard-coded example inputs in `main.py` with a small command-line interface that selects a data source, stock code, date range, K-line levels, and image output directory.

## Chosen approach

Use a dedicated, testable parsing module and keep `main.py` as a thin orchestration entry point. This avoids coupling argument validation and date-default logic to plotting and data fetching.

## Command-line interface

```text
python main.py \
  --data-src baostock \
  --code sz.000001 \
  --start 2025-01-01 \
  --end 2026-01-01 \
  --kl-type K_WEEK,K_DAY,K_30M,K_5M \
  --output-dir output
```

Arguments:

- `--data-src`: `baostock`, `akshare`, `ccxt`, or `csv`; defaults to `baostock`.
- `--code`: stock or instrument code; defaults to the existing example, `sz.000001`.
- `--start`: ISO date (`YYYY-MM-DD`). When supplied, it applies to every selected level.
- `--end`: optional ISO date. When omitted, the data source continues to receive `None`, preserving its existing latest-data behavior.
- `--kl-type`: a comma-separated list of `KL_TYPE` names. It defaults to `K_WEEK,K_DAY,K_30M,K_5M`.
- `--output-dir`: image destination directory; defaults to `output`.

Unknown values and malformed dates terminate through argparse with a clear error. No trading-calendar normalization, retry policy, or network-timeout behavior is included in this feature.

## Level-specific start dates

When `--start` is omitted, the CLI computes a start date relative to the current calendar date for each selected level:

| Level | Lookback |
| --- | ---: |
| `K_WEEK` | 2400 days |
| `K_DAY` | 1200 days |
| `K_30M` | 180 days |
| `K_5M` | 20 days |

Other levels receive `None` unless an explicit `--start` is supplied.

`CChan` currently distributes one `begin_time` to every data source request. It will be extended to also accept a mapping keyed by `KL_TYPE`, while retaining the scalar input behavior for all current callers. Each data-source instance receives the date for the level it is loading.

## Output

The entry point creates the requested directory if necessary and saves the static image as `<output-dir>/<code>.png`. The repository ignores `/output/` so default generated images do not appear in Git status.

## Structure and tests

- A small CLI module owns the parser, enum mapping, ISO date validation, and level-specific start-date calculation.
- `main.py` owns the existing Chan/plot configuration and calls that module.
- `Chan.py` selects a per-level beginning date when supplied a mapping.
- Focused tests cover parser defaults, multi-level parsing, explicit-start override, invalid input, default lookbacks, and per-level forwarding to a data source.

## Compatibility

Existing callers that pass scalar `begin_time` and `end_time` retain their current behavior. The default data source remains BaoStock and the existing plotting configuration remains unchanged.
