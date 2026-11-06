code2=open('/work/run.py').read().split("active=M.any")[0]
exec(compile(code2+r'''
mx=0
for y in range(ny):
    for x in range(nx):
        if sea[y,x]:
            rr=runs(H[:,y,x]); 
            if rr: mx=max(mx,max(e-s+1 for s,e in rr))
print('max hot run', mx, 'cells with any hot', (H.any(0)&sea).sum())
print('per-day hot cells', H.sum(axis=(1,2))[:20])
print('sample T vs thr', T[0,10,10], thrS[doys[0]-1,10,10], doys[0])
''','d','exec'))