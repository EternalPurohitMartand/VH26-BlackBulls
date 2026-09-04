# ml_pipeline/predictor.py
import joblib
import os
import ast
import pandas as pd
from ml_pipeline.dataset_builder import FeatureExtractionVisitor

TIER_HIGH = "HIGH"
TIER_MEDIUM = "MEDIUM"
TIER_LOW = "LOW"

TIER_CONFIG = {
    TIER_HIGH:   {"action": "BLOCK_BUILD", "color": "\033[91m", "reset": "\033[0m", "label": "HIGH RISK"},
    TIER_MEDIUM: {"action": "WARN_ONLY",  "color": "\033[93m", "reset": "\033[0m", "label": "MEDIUM RISK"},
    TIER_LOW:    {"action": "PASS",       "color": "\033[92m", "reset": "\033[0m", "label": "LOW RISK"},
}

def categorize_risk(confidence):
    """Convert raw ML probability (0-100) into a 3-tier risk category.

    Returns dict with keys: tier, action, label, confidence, color, reset
    """
    if confidence >= 80:
        tier = TIER_HIGH
    elif confidence >= 40:
        tier = TIER_MEDIUM
    else:
        tier = TIER_LOW

    cfg = TIER_CONFIG[tier]
    return {
        "tier": tier,
        "action": cfg["action"],
        "label": cfg["label"],
        "color": cfg["color"],
        "reset": cfg["reset"],
        "confidence": confidence,
    }

def get_leak_confidence(filepath):
    """Runs live ML inference to predict the probability of a leak."""
    model_path = os.path.join(os.path.dirname(__file__), "leak_model.pkl")

    if not os.path.exists(model_path):
        return None

    model = joblib.load(model_path)

    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    visitor = FeatureExtractionVisitor()
    visitor.visit(tree)

    df = pd.DataFrame([visitor.features])

    probabilities = model.predict_proba(df)
    leak_confidence = probabilities[0][1] * 100

    return leak_confidence