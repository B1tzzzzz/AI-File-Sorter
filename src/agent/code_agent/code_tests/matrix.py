import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

import seaborn as sns


dataset = pd.read_csv("chip_dataset.csv")
dataset = dataset.drop(index=range(0, 2192))
dataset = dataset.drop(columns=['Unnamed: 0', 'Product', 'Type', 'Release Date', 'Foundry', 'Vendor', 'FP16 GFLOPS', 'FP32 GFLOPS', 'FP64 GFLOPS'])
dataset = dataset.dropna()

cor = dataset.corr()    
print(cor)
sns.heatmap(cor, annot=True, fmt='.2f', cmap="coolwarm", vmin = -1, vmax = 1)
plt.show()


