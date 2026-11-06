code3=open('/work/run.py').read().split("H=np.zeros")[0]
exec(compile(code3+r'''
# fraction of baseline values exceeding threshold for a doy
for d in [153,180,200]:
    md=dt.date(2000,1,1)+dt.timedelta(d-1)
    vals=[S[idx[dt.date(Y,md.month,md.day)+dt.timedelta(k)]][sea] for Y in range(1992,2003) for k in range(-5,6)]
    P=np.stack(vals)
    print(d, 'frac>=thrS', (P>=thrS[d-1][sea]).mean(), 'frac>=thr raw', (P>=thr[d][sea]).mean(), 'mean P',P.mean(), 'thrS mean', thrS[d-1][sea].mean())
# target mean vs baseline mean
print('target mean', T[:,sea].mean(), 'target mean by month', [T[i:i+30][:,sea].mean() for i in (0,30,60)])
''','d','exec'))