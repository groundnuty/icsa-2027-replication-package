import numpy as np, pickle

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/mhw_state.pkl","rb") as f: S = pickle.load(f)

sea_pkl = D["sea"]
sea2 = np.isfinite(D["sst_target"]).all(axis=0)
print("shapes:", sea_pkl.shape, sea2.shape, sea_pkl.dtype, sea2.dtype)
print("sea equal:", bool((sea_pkl == sea2).all()))

cell_idx = np.flatnonzero(sea2)
cell_idx_ref = S["cell_idx"]
print("cell_idx dtype/len:", cell_idx.dtype, len(cell_idx), "ref:", cell_idx_ref.dtype, len(cell_idx_ref))
print("first 5:", cell_idx[:5], cell_idx_ref[:5])
print("last 5:", cell_idx[-5:], cell_idx_ref[-5:])
diff = np.flatnonzero(cell_idx != cell_idx_ref)
print("num diffs:", len(diff))
if len(diff):
    k = diff[0]
    print("first diff at", k, cell_idx[k], cell_idx_ref[k])
    print("context:", cell_idx[k-2:k+3], cell_idx_ref[k-2:k+3])
