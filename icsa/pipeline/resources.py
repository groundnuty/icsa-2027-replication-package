"""What the pipeline needs besides the run directories: instances, required extents, references, layout indexes.

Ground truth per instance is large (the SST of the whole required baseline), so `Production` builds one
`Reference` at a time and keeps only the last one; the pipeline processes runs grouped by instance.
Tests inject their own `Resources`.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np

from icsa import grid, paths
from icsa.extent import PartedExtent
from icsa.instruments.layout import LayoutIndex
from icsa.records import Instance, Layout, Option
from icsa.scoring.reference import Reference

from .loadrec import PipelineError


def with_frozen_truth(recomputed: Reference, frozen_cell_mask: np.ndarray,
                      frozen_events: list[tuple[int, int]]) -> Reference:
    """Score against the frozen, registered ground truth: `gt` becomes the frozen mask and events, and the
    recomputed detection (`full`, needed for the counterfactual) must equal it, cell-day for cell-day and
    event for event. A difference is a named failure (`truth_mismatch`), never scored silently."""
    from icsa import refdet
    rec = recomputed.full
    got_ev = sorted((int(e.onset), int(e.end)) for e in rec.events)
    if frozen_cell_mask.shape != rec.cell_mask.shape:
        raise PipelineError("truth_mismatch", f"shape {frozen_cell_mask.shape} frozen vs {rec.cell_mask.shape} recomputed")
    diff = int((frozen_cell_mask != rec.cell_mask).sum())
    if diff or got_ev != sorted((int(a), int(b)) for a, b in frozen_events):
        raise PipelineError("truth_mismatch", f"recomputed detection differs from the frozen truth: {diff} cell-days, "
                            f"events {got_ev} vs {sorted(tuple(map(int, e)) for e in frozen_events)}")
    gt = dataclasses.replace(rec, cell_mask=frozen_cell_mask, active=frozen_cell_mask.any(axis=(1, 2)),
                             events=[refdet.Event(int(a), int(b)) for a, b in frozen_events])
    return dataclasses.replace(recomputed, gt=gt)


class Resources:
    """The interface. `instance_id`s are those of `icsa.records.Instance`."""

    def instances(self) -> list[Instance]:
        raise NotImplementedError

    def required(self, instance_id: str) -> PartedExtent:
        raise NotImplementedError

    def reference(self, instance_id: str) -> Reference:
        raise NotImplementedError

    def index(self, layout: Layout) -> LayoutIndex:
        raise NotImplementedError

    def dir_sizes(self, layout: Layout) -> dict[str, int] | None:
        """Directory (as the agent lists it) -> number of entries, for the listing summary."""
        return None

    def preload(self) -> None:
        """Build what workers can share before they fork. Nothing, by default."""

    def local_roots(self, option: Option, run_dir: Path) -> list[Path]:
        return [run_dir / "downloads"] if option == Option.D else []


class Production(Resources):
    """The study's inputs: the committed instance manifest (#5), `icsa.refdet` on the S1 files (#4) and
    the full layout index (#9, `fullindex.load_full_index`), the only one that names in-memory sources by
    content and gate lines by Onedata id. A bare `LayoutIndex.load` of its file has neither, which would make every
    in-memory decode `unknown` and every gate line unplaced (`LayoutIndex.load` refuses it)."""

    def __init__(self, index_root: Path | None = None, s1_dir_name: str = "s1z", mount_root: Path | None = None,
                 data_dir: Path | None = None):
        from icsa.instances import load as L
        self._L = L
        self._manifest = L.load_instances()
        self._records = {r["instance"]["instance_id"]: r for r in self._manifest["instances"]}
        self._masks = L.load_sea_masks(L.DATA / self._manifest["sea_masks"]["file"],
                                       self._manifest["sea_masks"]["sha256"])
        self.index_root = index_root
        self._index: LayoutIndex | None = None
        self.s1_dir_name, self.mount_root = s1_dir_name, mount_root
        self._cache: tuple[str, Reference | PipelineError] | None = None     # one instance at a time
        # The S1 copy the recomputation reads: by default the one the agents read (lossless, #3; with_frozen_truth checks
        # the result). `paths.S1_DIR`, the uncompressed original, is not on the run host.
        self.data_dir = Path(data_dir) if data_dir else Path(index_root or paths.DATA_ROOT) / s1_dir_name

    def instances(self) -> list[Instance]:
        return self._L.load_all_instances(self._manifest)

    def _rec(self, instance_id: str) -> dict:
        try:
            return self._records[instance_id]
        except KeyError:
            raise PipelineError("unknown_instance", instance_id) from None

    def required(self, instance_id: str) -> PartedExtent:
        return self.reference(instance_id).required      # every run is scored, so the reference is needed anyway

    def _loader(self):
        if self.data_dir is None:
            return None                                     # refdet.load_sst: paths.S1_DIR
        from icsa.refdet import data as D
        index = D.s1_index(self.data_dir)

        def load(box, days):
            import netCDF4
            out = np.full((len(days), *box.shape), np.nan, np.float32)
            with D.NETCDF_LOCK:
                for k, d in enumerate(days):
                    with netCDF4.Dataset(D.s1_file(index, d)) as ds:
                        a = D._read_var(ds, box, 0 if ds["analysed_sst"].ndim == 3 else slice(None))
                    out[k] = a.reshape(box.shape)
            return out
        return load

    def reference(self, instance_id: str) -> Reference:
        """Scored against the frozen truth (`oracle_real.load_truth`: sha256 of the packed masks verified, events
        checked against the manifest); the SST is recomputed only for the counterfactual, and must reproduce it.
        A failure is cached, so the instance's other runs fail the same way without a second recomputation."""
        if self._cache and self._cache[0] == instance_id:
            if isinstance(self._cache[1], PipelineError):
                raise self._cache[1]
            return self._cache[1]
        from icsa import refdet
        from icsa.harness.oracle_real import load_truth
        from icsa.scoring.reference import build_reference
        self._cache = None                       # release the previous instance before loading the next
        rec = self._rec(instance_id)
        try:
            truth = load_truth(rec)
            req = self._L.required_extent(rec, self._masks[rec["instance"]["region_id"]])
            ref = with_frozen_truth(build_reference(self._L.instance(rec), req, refdet, self._loader()),
                                    truth.cell_mask, truth.events)
        except PipelineError as e:
            self._cache = (instance_id, e)
            raise
        self._cache = (instance_id, ref)
        return ref


    def index(self, layout: Layout) -> LayoutIndex:
        if self._index is None:
            from icsa.instruments.fullindex import load_full_index
            self._index = load_full_index(self.index_root)        # one index holds both layouts
        return self._index

    def preload(self) -> None:
        self.index(Layout.S1)

    def dir_sizes(self, layout: Layout) -> dict[str, int] | None:
        return {self.s1_dir_name: grid.NDAYS} if layout == Layout.S1 else None

    def local_roots(self, option: Option, run_dir: Path) -> list[Path]:
        if option == Option.D:
            return [run_dir / "downloads"]
        if option in (Option.M, Option.M_PLUS) and self.mount_root:
            return [Path(self.mount_root)]
        return []
