"""fsspec filesystem over the local RangeServer, shaped like a REST fsspec client."""
from __future__ import annotations

import shutil

import requests
from fsspec.spec import AbstractBufferedFile, AbstractFileSystem


class RangeFS(AbstractFileSystem):
    protocol = "simrange"
    cachable = False

    def __init__(self, url: str, *, block_size: int = 4 * 2**20, cache_type: str = "readahead",
                 page_limit: int = 1000, listing: str = "client", **kwargs):
        """listing: "client" lists as the official Onedata fsspec client does (#10): one
        request with limit=page_limit, isLast and nextPageToken ignored. "shim" is the
        T-unpaginated shim: it follows nextPageToken until isLast."""
        super().__init__(**kwargs)
        if listing not in ("client", "shim"):
            raise ValueError(listing)
        self.url = url.rstrip("/")
        self.block_size = block_size
        self.cache_type = cache_type
        self.page_limit = page_limit
        self.listing = listing
        self.session = requests.Session()

    @classmethod
    def _strip_protocol(cls, path):
        path = str(path)
        if path.startswith("simrange://"):
            path = path[len("simrange://"):]
        return path.strip("/")

    def _data_url(self, path):
        return f"{self.url}/data/{self._strip_protocol(path)}"

    def list_url(self, path) -> str:
        return f"{self.url}/list/{self._strip_protocol(path)}"

    def _list_page(self, path, token=None):
        params = {"limit": self.page_limit}
        if token is not None:
            params["token"] = token
        r = self.session.get(self.list_url(path), params=params)
        if r.status_code == 404:
            raise FileNotFoundError(path)
        r.raise_for_status()
        return r.json()

    def ls(self, path, detail=True, **kwargs):
        path = self._strip_protocol(path)
        out, token = [], None
        while True:
            page = self._list_page(path, token)
            for e in page["children"]:
                name = f"{path}/{e['name']}" if path else e["name"]
                out.append({"name": name, "size": e["size"],
                            "type": "directory" if e["type"] == "DIR" else "file"})
            if self.listing == "client" or page["isLast"]:
                break
            token = page["nextPageToken"]
        return out if detail else [e["name"] for e in out]

    def info(self, path, **kwargs):
        path = self._strip_protocol(path)
        if path:
            r = self.session.head(self._data_url(path))
            if r.status_code == 200:
                return {"name": path, "size": int(r.headers["Content-Length"]), "type": "file"}
        # A directory check, not a listing: HEAD delivers no entries (the listing
        # summary counts GET requests only).
        r = self.session.head(self.list_url(path))
        if r.status_code == 404:
            raise FileNotFoundError(path)
        r.raise_for_status()
        return {"name": path, "size": 0, "type": "directory"}

    def cat_file(self, path, start=None, end=None, **kwargs):
        if start is None and end is None:
            r = self.session.get(self._data_url(path))
        else:
            size = self.info(path)["size"] if (start is not None and start < 0) or (end is not None and end < 0) else None
            if size is not None:
                start = size + start if start is not None and start < 0 else start
                end = size + end if end is not None and end < 0 else end
            start = start or 0
            rng = f"bytes={start}-" if end is None else f"bytes={start}-{end - 1}"
            r = self.session.get(self._data_url(path), headers={"Range": rng})
        if r.status_code == 404:
            raise FileNotFoundError(path)
        if r.status_code == 416:
            return b""
        r.raise_for_status()
        return r.content

    def get_file(self, rpath, lpath, **kwargs):
        """Download the whole file with one GET, no Range (the D path)."""
        with self.session.get(self._data_url(rpath), stream=True) as r:
            if r.status_code == 404:
                raise FileNotFoundError(rpath)
            r.raise_for_status()
            with open(lpath, "wb") as f:
                shutil.copyfileobj(r.raw, f)

    def _open(self, path, mode="rb", block_size=None, autocommit=True, cache_options=None, **kwargs):
        if mode != "rb":
            raise NotImplementedError("read-only")
        return RangeFile(self, path, mode=mode,
                         block_size=block_size or self.block_size,
                         cache_type=kwargs.pop("cache_type", self.cache_type),
                         cache_options=cache_options, **kwargs)


class RangeFile(AbstractBufferedFile):
    def _fetch_range(self, start, end):
        if end <= start:
            return b""
        r = self.fs.session.get(self.fs._data_url(self.path),
                                headers={"Range": f"bytes={start}-{end - 1}"})
        if r.status_code == 416:
            return b""
        r.raise_for_status()
        return r.content
