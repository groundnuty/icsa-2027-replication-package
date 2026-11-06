code4=open('/work/run.py').read().split("H=np.zeros")[0]
exec(compile(code4+r'''
m=sea
for d in range(150,211,6):
    print(d, np.round(np.nanmean(thr[d][m]),2), np.round(np.nanmean(thrS[d-1][m]),2), np.round(np.nanmean(clim[d][m]),2))
''','d','exec'))