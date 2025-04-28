import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

# Buat dataset
np.random.seed(42)
x = np.random.rand(100, 1) * 10  # Nilai x antara 0-10
a_true, b_true = 2.5, 5  # Nilai sebenarnya dari a dan b
y = a_true * x + b_true + np.random.randn(100, 1) * 2  # Tambahkan noise

# Bagi dataset menjadi train dan test
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

# Inisialisasi dan latih model regresi linear
model = LinearRegression()
model.fit(x_train, y_train)

# Prediksi dan dapatkan nilai a dan b
predicted_a = model.coef_[0][0]
predicted_b = model.intercept_[0]

print(f"Nilai a yang diprediksi: {predicted_a}")
print(f"Nilai b yang diprediksi: {predicted_b}")

# Visualisasi hasil regresi
plt.scatter(x, y, label="Data")
plt.plot(x, model.predict(x), color='red', label="Regresi Linear")
plt.xlabel("x")
plt.ylabel("y")
plt.legend()
plt.show()