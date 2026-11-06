import datetime as dt
def doy_c(d):
    return (d.month - 1) * 31 + min(d.month, 8) // 2 + d.day  # placeholder
