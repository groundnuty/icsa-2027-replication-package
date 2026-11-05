"""Option-specific conveniences of the shipped fsspec client, loaded by sitecustomize.

NOT enforcement (the gate enforces; see sandbox/README.md). The only code in a data path written for
this study, besides the gate's listing shim for T-unpaginated.

Option D: in-place remote reads fail at once with a clear message instead of a gate refusal deep in the
client, and `fs.get(remote, local)` works by streaming the whole file (the shipped `get_file` reads
through `open()` in ranges, which D forbids).
"""
import os

D_MESSAGE = ("In this sandbox, files cannot be read remotely in place; "
             "download whole files with fs.get(remote_path, local_path) first.")


def _install_d() -> None:
    from onedatarestfsspec import core

    def _fetch_range(self, start, end):
        raise OSError(D_MESSAGE)

    core.OnedataFile._fetch_range = _fetch_range
    orig_cat = core.OnedataFileSystem.cat_file

    def cat_file(self, path, start=None, end=None, **kw):
        if start is not None or end is not None:
            raise OSError(D_MESSAGE)
        return orig_cat(self, path, start=start, end=end, **kw)

    def get_file(self, rpath, lpath, callback=None, outfile=None, **kw):
        if self.isdir(rpath):  # as fsspec's own get_file: a remote directory becomes a local one
            os.makedirs(lpath, exist_ok=True)
            return
        if os.path.isdir(lpath):  # as fsspec: a download into an existing directory keeps the file name
            lpath = os.path.join(lpath, os.path.basename(rpath.rstrip("/")))
        os.makedirs(os.path.dirname(os.path.abspath(lpath)), exist_ok=True)
        space, path = self._split_onedata_path(self._strip_protocol(rpath))
        it = self.client.iter_file_content(space, file_path=path)
        out = outfile if outfile is not None else open(lpath, "wb")
        try:
            for chunk in it:
                out.write(chunk)
        finally:
            if outfile is None:
                out.close()

    core.OnedataFileSystem.cat_file = cat_file
    core.OnedataFileSystem.get_file = get_file


READ_TIMEOUT = (8, 14400)


def _install_rest_timeout() -> None:
    """All REST options (identical): the shipped filesystem passes its own default timeout=30 (a 30 s read
    timeout) down to the HTTP client, overriding the client's module default, so both are replaced.
    Under D the gate stores a whole file before the first byte (about an hour for a few GB at 10 Mbit/s),
    so a 30 s read timeout would fail every large download. The filesystem's timeout is forced to
    READ_TIMEOUT whatever the caller passes, so the setting is the same for T, T-unpaginated and D."""
    from onedatafilerestclient import http_client
    from onedatarestfsspec import core
    http_client._DEFAULT_TIMEOUT = READ_TIMEOUT
    orig_init = core.OnedataFileSystem.__init__

    # the shipped __init__ takes keyword arguments only, so a caller cannot pass the timeout positionally
    def __init__(self, **kw):
        kw["timeout"] = READ_TIMEOUT
        orig_init(self, **kw)

    core.OnedataFileSystem.__init__ = __init__


if os.environ.get("ICSA_OPTION") in ("T", "T-unpaginated", "D"):
    _install_rest_timeout()
if os.environ.get("ICSA_OPTION") == "D":
    _install_d()
