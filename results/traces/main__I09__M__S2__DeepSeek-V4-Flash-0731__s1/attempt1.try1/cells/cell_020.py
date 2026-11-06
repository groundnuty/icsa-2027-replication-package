
import pandas as pd

target_start = pd.Timestamp('2022-06-01')
target_dates = pd.date_range(target_start, periods=92, freq='D')
print("Index 0:", target_dates[0].strftime('%Y-%m-%d'))
print("Index 7:", target_dates[7].strftime('%Y-%m-%d'))
print("Index 17:", target_dates[17].strftime('%Y-%m-%d'))
print("Index 21:", target_dates[21].strftime('%Y-%m-%d'))
print("Index 43:", target_dates[43].strftime('%Y-%m-%d'))
print("Index 49:", target_dates[49].strftime('%Y-%m-%d'))
print("Index 53:", target_dates[53].strftime('%Y-%m-%d'))
print("Index 70:", target_dates[70].strftime('%Y-%m-%d'))
print("Index 91:", target_dates[91].strftime('%Y-%m-%d'))
