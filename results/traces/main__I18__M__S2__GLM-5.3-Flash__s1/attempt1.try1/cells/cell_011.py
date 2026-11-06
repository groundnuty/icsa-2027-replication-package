import numpy as np
thr = np.load("/tmp/thr.npy")
tgt = np.load("/tmp/tgt.npy")

finite_target = np.isfinite(tgt).all(axis=0)    # sea cells: finite every target day
finite_thr = np.isfinite(thr).all(axis=0)
print("n sea cells:", finite_target.sum(), " n cells with finite thr:", finite_thr.sum())
print("sea cells == finite-thr cells:", np.array_equal(finite_target, finite_thr))
print("n cells with thr NaN somewhere:", (~finite_thr).sum())

# Among sea cells, is thr finite everywhere?
print("sea cells all finite thr:", np.isfinite(thr[:, finite_target]).all())
# Any cell partially finite target but not all?
partial = np.isfinite(tgt).any(axis=0) & ~finite_target
print("partial cells:", partial.sum())

# Also: do sea cells have finite baseline data on all pool days? implied by finite thr
np.save("/tmp/sea.npy", finite_target)
