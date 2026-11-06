
print('NaN in thr raw, sea cells:', np.isnan(thr[:,finite_all]).sum(), ' clim:', np.isnan(clim[:,finite_all]).sum())
print('NaN in thrS sea cells:', np.isnan(thrS[:,finite_all]).sum(), 'climS:', np.isnan(climS[:,finite_all]).sum())
print('pool sizes: min/max count finite', min(np.isfinite(vals[pools[d]]).sum(axis=0)[finite_all].min() for d in pools))
# how many sea cells have NaN in baseline at all
bl = vals[[tpos[t] for t in base if True]] if False else None
