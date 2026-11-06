
import numpy as np, datetime as dt

hot = np.load('/tmp/mhw/hot.npy')
maskA = np.load('/tmp/mhw/maskA.npy')
sea2 = np.load('/tmp/mhw/sea2.npy')
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(92)]

active = maskA.any(axis=1)
print("active Jun 10..20:", [(str(t), bool(a)) for t,a in zip(tdates[9:20], active[9:20])])
print("active Jul 20..28:", [(str(t), bool(a)) for t,a in zip(tdates[49:57], active[49:57])])
print("active Aug 1..5:", [(str(t), bool(a)) for t,a in zip(tdates[61:66], active[61:66])])

# inspect a few cells around Jul 20-28
cand = np.where(hot[52] & sea2)[0][:4]  # cells hot on Jul 23
for c in cand:
    s = ''.join('#' if hot[k,c] else ('.' if not maskA[k,c] else 'M') for k in range(48,66))
    print(f"cell {c} (lat idx {c//60}, lon idx {c%60}) Jul19..Aug5 hot/mask: {s}")

# how many cells are in MHW on Jun 15 and Jul 24?
print("cells in MHW Jun15:", int(maskA[14].sum()), " Jun16:", int(maskA[15].sum()))
print("cells in MHW Jul23:", int(maskA[52].sum()), " Jul24:", int(maskA[53].sum()), " Aug3:", int(maskA[63].sum()), " Aug4:", int(maskA[64].sum()))
