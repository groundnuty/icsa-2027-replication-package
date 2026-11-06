
nanthr=np.isnan(thr_s).any(axis=0)
print('sea cells with nan thr:', (sea & nanthr).sum(), ' land-ish cells nan thr:', nanthr.sum())
print('target nan cells all-time:', np.isnan(tv).any(axis=0).sum())
# sanity: hot fraction
print(hot[:, sea].mean(), mhw[:,sea].mean())
print(np.nanmax(tv), np.nanmin(tv))
