import numpy as np, datetime
hot = np.load('hot.npy')
tgt = np.load('target.npy').astype(np.float64)
thresh = np.load('thresh.npy')
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]
# spatial pattern of hot cells on 08-08 (idx 68)
i68 = 68
m = hot[i68]
print('hot cells on', dates[i68], ':', m.sum())
ii, jj = np.where(m)
print('some hot cells (i,j):', list(zip(ii[:10], jj[:10])))
# check a specific hot cell's SST & threshold around Aug 5-12
k = 0
i,j = ii[0], jj[0]
print('cell', (i,j))
for d in range(63, 75):
    di = 151 + d
    print(dates[d], 'SST', tgt[d,i,j].round(3), 'thresh', thresh[di,i,j].round(3), 'hot', bool(hot[d,i,j]))
# regional mean SST around then
print('regional mean SST Aug 4..12:')
for d in range(64, 73):
    print(' ', dates[d], round(np.nanmean(tgt[d]),3))
