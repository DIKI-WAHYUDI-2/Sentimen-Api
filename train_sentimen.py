from sklearn.model_selection import train_test_split
import pandas as pd 

df = pd.read_excel('./data/data-berita.xlsx')

x = df[['title']]
y = df['Sentimen']

X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

train_data = pd.concat([X_train, y_train], axis=1)
test_data = pd.concat([X_test, y_test], axis=1)

train_data.to_csv("train_data.csv", index=False)
test_data.to_csv("test_data.csv", index=False)

print("Jumlah Data Latih:", len(X_train))
print("Jumlah Data Uji:", len(X_test))
print("\nDistribusi Sentimen di Data Latih:")
print(y_train.value_counts())

print("\nDistribusi Sentimen di Data Uji:")
print(y_test.value_counts())
