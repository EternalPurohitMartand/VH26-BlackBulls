# ml_pipeline/train_model.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def train():
    dataset_path = os.path.join(os.path.dirname(__file__), "dataset.csv")
    model_path = os.path.join(os.path.dirname(__file__), "leak_model.pkl")

    if not os.path.exists(dataset_path):
        print(f"❌ Error: {dataset_path} not found. Run dataset_builder.py first.")
        return

    print("📊 Loading dataset...")
    df = pd.read_csv(dataset_path)

    # Features (Inputs) - everything except the file name and the target label
    X = df.drop(columns=["file_name", "is_leak"])
    
    # Target (Output) - what we are trying to predict
    y = df["is_leak"]

    print("🧠 Training Random Forest Classifier...")
    # Initialize the model (Random Forest is highly accurate for code pattern classification)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    # Train the model on your AST data
    model.fit(X, y)

    # Save the trained model to a file so the CI/CD pipeline can use it
    joblib.dump(model, model_path)
    
    print(f"✅ Model trained successfully!")
    print(f"💾 Saved model to: {model_path}")
    
    # Let's do a quick sanity check on its accuracy
    accuracy = model.score(X, y) * 100
    print(f"🎯 MVP Training Accuracy: {accuracy:.2f}%")

if __name__ == '__main__':
    train()
    