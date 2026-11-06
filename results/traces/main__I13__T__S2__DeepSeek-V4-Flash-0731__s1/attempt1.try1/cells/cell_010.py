
import numpy as np

dates = np.array([
    np.datetime64('1992-01-01'),
    np.datetime64('1992-02-28'),
    np.datetime64('1992-02-29'),
    np.datetime64('1992-03-01'),
    np.datetime64('1992-12-31'),
    np.datetime64('2021-06-01'),
    np.datetime64('2021-08-31'),
])

# Check month extraction
months_64M = dates.astype('datetime64[M]')
print("Months (as M):", months_64M)
print("Months (as int):", months_64M.astype(np.int64))

months_int = months_64M.astype(np.int64) % 12 + 1
print("Month numbers:", months_int)

# Check day extraction
days_64D = dates.astype('datetime64[D]')
days_int = days_64D.astype(np.int64) - months_64M.astype(np.int64) + 1
print("Day numbers:", days_int)

# Check a specific date
print("\nCheck 1992-01-01:")
print("  as M:", np.datetime64('1992-01-01').astype('datetime64[M]'))
print("  as D:", np.datetime64('1992-01-01').astype('datetime64[D]'))
print("  M as int:", np.datetime64('1992-01-01').astype('datetime64[M]').astype(np.int64))
print("  D as int:", np.datetime64('1992-01-01').astype('datetime64[D]').astype(np.int64))

# The issue: np.datetime64[M] truncates to month, np.datetime64[D] gives days since epoch
# For 1992-01-01: M gives days since 1970-01 to 1992-01, D gives days since 1970-01-01 to 1992-01-01
# M int = number of months since 1970-01 = 22*12 = 264
# D int = number of days since 1970-01-01
# So days_in_month = D - M*30 (approx, since M is months not days)

# Actually, when converting datetime64[M] to int, we get the number of months since epoch
# When converting datetime64[D] to int, we get the number of days since epoch
# The difference D - M_as_days gives days within month
# But M_as_days = M_int * 30 (average) is not exact

# Better approach: use pd.Timestamp or datetime
import datetime
for d in dates:
    dt = d.astype('datetime64[D]').astype(datetime.datetime)
    print(d, "-> month:", dt.month, "day:", dt.day)
