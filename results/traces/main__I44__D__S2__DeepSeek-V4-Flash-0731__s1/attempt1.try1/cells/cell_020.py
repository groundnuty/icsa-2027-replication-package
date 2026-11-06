
import numpy as np
import pandas as pd

# Verify the regional events
target_dates = pd.date_range('2004-06-01', '2004-08-31', freq='D')
# Active days: indices 67-72
for idx in [67, 68, 69, 70, 71, 72]:
    print(f"Day {idx}: {target_dates[idx].date()}")

# The event onset = target_dates[67], end = target_dates[72]
print(f"\nEvent: {target_dates[67].date()} to {target_dates[72].date()}")
