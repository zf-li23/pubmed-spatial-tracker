"""Ensemble models: RF, AdaBoost, XGBoost."""

from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier

MODELS = {
    "rf": lambda: RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=42),
    "ada": lambda: AdaBoostClassifier(n_estimators=100, random_state=42),
}

try:
    from xgboost import XGBClassifier
    MODELS["xgb"] = lambda: XGBClassifier(n_estimators=200, use_label_encoder=False,
                                          eval_metric="logloss", random_state=42, n_jobs=-1)
except ImportError:
    pass
