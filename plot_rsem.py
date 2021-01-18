import matplotlib.pyplot as plt
import pandas as pd


csv_file = 'turri_2016-feb-may_VLP.csv'
df = pd.read_csv(csv_file, index_col='utcdatetime')
df = df.sort_values(by='utcdatetime')
df.index = pd.to_datetime(df.index)

df.rms = df.rms.rolling(window=200).median()
plt.plot(df.index, df.rms)
plt.yscale('log')
plt.show()
