dates = sorted(re.search(r'(\d{8})', n).group(1) for n in names)
print(dates[0], dates[-1])
import collections
yrs = collections.Counter(d[:4] for d in dates); print(sorted(yrs.items()))
print(ds.analysed_sst.attrs)
print(ds.attrs['comment'])