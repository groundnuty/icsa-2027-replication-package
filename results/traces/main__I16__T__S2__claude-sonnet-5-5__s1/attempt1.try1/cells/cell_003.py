
print(pd.Series(b.time.values).diff().value_counts().head(3))
