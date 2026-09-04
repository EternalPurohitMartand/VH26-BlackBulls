# ml_pipeline/predictor.py
import joblib
import os
import ast
import pandas as pd
from ml_pipeline.dataset_builder import FeatureExtractionVisitor

def get_leak_confidence(filepath):
    """Runs live ML inference to predict the probability of a leak."""
    model_path = os.path.join(os.path.dirname(__file__), "leak_model.pkl")
    
    if not os.path.exists(model_path):
        return None
        
    # Load the trained AI model
    model = joblib.load(model_path)
    
    # Extract structural features from the file being scanned
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
        
    visitor = FeatureExtractionVisitor()
    visitor.visit(tree)
    
    # Format for the model
    df = pd.DataFrame([visitor.features])
    
    # predict_proba returns an array: [[probability_safe, probability_leak]]
    probabilities = model.predict_proba(df)
    leak_confidence = probabilities[0][1] * 100
    
    return leak_confidence