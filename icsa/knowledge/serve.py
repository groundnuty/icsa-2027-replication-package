"""Launcher of the pinned onedata-mcp (#6). THIS PROCESS IS NOT THE STOCK `onedata-mcp` ENTRYPOINT.

It does one thing before handing over to the server's own `onedata_mcp.main:main`: it makes `icsa-knowledge-plane/<short sha>`
(from $ICSA_KNOWLEDGE_UA) the User-Agent of every httpx client the server creates, so the plane's REST requests can be told
apart in platform records (Traefik logs neither user nor token). The server's source is not touched (pin.verify_pin checks the
clone is at the pinned commit with no change); no tool, schema or description is altered.

Standalone on purpose: it runs in the server's own virtualenv (stdlib + httpx + onedata_mcp only), not in this project's.
"""
import os
import sys

import httpx

UA = os.environ.get("ICSA_KNOWLEDGE_UA", "")
if not UA.startswith("icsa-knowledge-plane/"):
    sys.exit("serve.py: ICSA_KNOWLEDGE_UA must be set to icsa-knowledge-plane/<short sha>")

_orig_init = httpx.AsyncClient.__init__


def _init(self, *args, **kwargs):
    headers = httpx.Headers(kwargs.pop("headers", None) or {})
    headers["User-Agent"] = UA
    _orig_init(self, *args, headers=headers, **kwargs)


httpx.AsyncClient.__init__ = _init

from onedata_mcp.main import main  # noqa: E402  (after the patch; the server builds its clients per request)

if __name__ == "__main__":
    main()
