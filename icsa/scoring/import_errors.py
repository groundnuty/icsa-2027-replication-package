"""ImportErrors the agent saw, by module (science, #2, 10:52Z). dask isn't in the image, and `open_mfdataset` may come more
naturally under D and M at S1, so a missing package may not land equally on the options. Counted from what the agent was given,
the same text in every option. Lower bound: a tool output over the cap can lose its last lines."""
from __future__ import annotations

import re
from collections import Counter

_ERROR = re.compile(r"^(?:ModuleNotFoundError|ImportError)\b:?(.*)$", re.M)
_NAMED = re.compile(r"No module named ['\"]([\w.]+)['\"]")
_FROM = re.compile(r"cannot import name ['\"][\w.]+['\"] from ['\"]([\w.]+)['\"]")
_QUOTED = re.compile(r"['\"]([A-Za-z_][\w.]*)['\"]")       # "chunk manager 'dask' is not available", as xarray puts it
UNNAMED = "(unnamed)"


def _module(message: str) -> str:
    m = _NAMED.search(message) or _FROM.search(message) or _QUOTED.search(message)
    return m.group(1).split(".")[0] if m else UNNAMED


def import_errors(turns) -> dict[str, int] | None:
    """Module -> how many tool outputs ended in an error naming it (one traceback chain counts once). None: no turn recorded,
    so nothing was observed; {}: turns, and no such error."""
    if not turns:
        return None
    n: Counter = Counter()
    for t in turns:
        for text in t.tool_outputs or ():
            n.update({_module(m.group(1)) for m in _ERROR.finditer(text)})
    return dict(n)
