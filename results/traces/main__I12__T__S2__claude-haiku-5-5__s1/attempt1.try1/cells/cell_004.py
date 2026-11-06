
import pandas as pd
t = pd.DatetimeIndex(sub.time.values)
print(t[0], t[-1], len(t), (pd.Timestamp('2009-08-31')-pd.Timestamp('1991-12-27')).days+1, t.is_monotonic_increasing, t.has_duplicates)
print(t.to_series().diff().value_counts().head())
