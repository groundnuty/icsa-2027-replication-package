import fsspec,re,pandas as pd
fs=fsspec.filesystem('onedata')
fl=sorted(fs.find('icsa2027_data_20261101T090944Z/s1z'))
have=pd.to_datetime([re.search(r'(\d{8})',f).group(1) for f in fl],format='%Y%m%d')
full=pd.date_range('1982-01-01','2023-12-31')
m=full.difference(have);print(len(m));print(m[:5],m[-5:])
# ranges
s=pd.Series(m);g=(s.diff()!=pd.Timedelta('1D')).cumsum()
print(s.groupby(g).agg(['min','max','count']))