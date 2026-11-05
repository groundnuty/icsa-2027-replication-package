"""The interim-snapshot command (#34, science item on snapshots). Lives OUTSIDE the frozen code hash (codestamp.ROOTS names icsa, config, protocol, tools,
pyproject.toml, uv.lock; this directory is none of them) and imports the frozen packages without changing them.

    python -m snapshot run --campaign-root R --t 2026-11-04T12:00:00Z --cap-s S --no-outcome report --final false --out DIR ...
    python -m snapshot cut ...        # only the cut: DIR/work/cut/{state.sqlite,run_dirs.txt,cut.json}
    python -m snapshot analyse ...    # the pipeline and the analysis on an existing cut
    python -m snapshot.fetch ...      # the store and the finished runs' directories from the run host into one local directory (see README.md)

A snapshot at t covers the runs whose counted start (`Store.counted_starts`: the first started attempt or the deferral, a retry never moves it) is at or
before t - cap. Each is finished as of t, exhausted as of t, or unfinished (never imputed). Runs that started later are out, finished or not.
"""
