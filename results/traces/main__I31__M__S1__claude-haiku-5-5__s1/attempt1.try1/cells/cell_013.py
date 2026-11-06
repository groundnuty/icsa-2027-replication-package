hot=(T>=th)&sea[None]
best=0
ny,nx=sea.shape
cnt=0
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=hot[:,y,x].astype(int)
        # longest run
        r=0;m=0
        for v in h:
            r=r+1 if v else 0; m=max(m,r)
        best=max(best,m)
        if m>=3: cnt+=1
print('longest run',best,'cells with run>=3',cnt)
print('hot per day',hot.sum(axis=(1,2))[::5])