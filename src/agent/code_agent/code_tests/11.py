import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import seaborn as sns

dataset = pd.read_csv("chip_dataset.csv")
dataset = dataset.drop(index=range(0, 2192))
r = []
dataset = dataset.dropna(subset=["Transistors (million)", "Freq (MHz)", "Process Size (nm)", 'Die Size (mm^2)', 'TDP (W)'])

x = dataset[["Die Size (mm^2)"]]
y = dataset[["TDP (W)"]]
X = dataset[["Freq (MHz)", "Transistors (million)", "Die Size (mm^2)", "Process Size (nm)"]]
print(X)
lr = LinearRegression()
lr.fit(x, y)
yPr = lr.predict(x)

lr2 = LinearRegression().fit(X, y)
yPr2 = lr2.predict(X)
r2 = r2_score(y, yPr2)
r = r2_score(y, yPr)

print(r, r2)
plt.figure(figsize=(10, 6))
plt.scatter(x, y)
plt.plot(x, yPr, c = 'r')
plt.title('Scatter plot and a Simple Linear Regression Model')
plt.ylabel("y")
plt.xlabel("x")
plt.show()
