import pandas as pd
import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Load dataset
file_path = "flood_dataset.csv"
df = pd.read_csv(file_path)

# Encode city names
city_encoder = LabelEncoder()
df["Encoded City"] = city_encoder.fit_transform(df["City"])

# Calculate dynamic thresholds for sensitivity
rainfall_mean = df["Rainfall"].mean()
rainfall_std = df["Rainfall"].std()
humidity_mean = df["Humidity"].mean()
humidity_std = df["Humidity"].std()
temperature_low = df["Temperature"].quantile(0.25)  # 25th percentile
temperature_high = df["Temperature"].quantile(0.75) # 75th percentile

def classify_flood_risk(row):
    """Classify flood risk with adaptive sensitivity."""
    if (row["Rainfall"] > (rainfall_mean + rainfall_std) and 
        row["Humidity"] > (humidity_mean + humidity_std) and 
        temperature_low <= row["Temperature"] <= temperature_high):
        return 2  # High risk
    elif (row["Rainfall"] > rainfall_mean and 
          row["Humidity"] > humidity_mean and 
          temperature_low <= row["Temperature"] <= temperature_high):
        return 1  # Moderate risk
    else:
        return 0  # Low risk

# Apply flood risk classification
df["Flood Risk Level"] = df.apply(classify_flood_risk, axis=1)

# Select features and target
X = df[["Encoded City", "Temperature", "Humidity", "Rainfall"]]
y = df["Flood Risk Level"]

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

# Evaluate model
print("Classification Report:")
print(classification_report(y_test, y_pred))
print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")

# Save model and encoder
joblib.dump(model, "flood_model.pkl")
joblib.dump(city_encoder, "city_encoder.pkl")
