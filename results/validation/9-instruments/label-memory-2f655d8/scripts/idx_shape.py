"""Read-only: how big are the index's files in elements and chunks? Stage timing of load_full_index."""
import time, resource, sys
t=time.time()
from icsa.instruments.fullindex import load_full_index
idx = load_full_index()
print("load_full_index s", round(time.time()-t,1), "maxrss_gib", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,3))
s1 = idx["s1z/sst_19920512.nc"]; s2 = idx["s2z/sst_s2.nc"]
for n, f in (("s1", s1), ("s2", s2)):
    print(n, "shape", f.shape, "itemsize", f.itemsize, "chunk_shape", f.chunk_shape, "n_chunks", f.chunks.shape[0], "filtered", f.filtered, "size", f.size, "contig", f.contiguous)
print("files", len(idx), "shas", len(idx.shas), "ids", len(idx.ids))
