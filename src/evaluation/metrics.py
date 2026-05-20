"""Evaluation metrics for multi-label and multi-class tasks."""

import numpy as np
from sklearn.metrics import (accuracy_score, f1_score, cohen_kappa_score,
                             jaccard_score, hamming_loss, roc_auc_score,
                             precision_recall_fscore_support)


def eval_multilabel(y_true, y_pred, y_prob=None):
    """Multi-label metrics."""
    res = {
        "jaccard": jaccard_score(y_true, y_pred, average="samples"),
        "hamming_loss": hamming_loss(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "micro_f1": f1_score(y_true, y_pred, average="micro", zero_division=0),
    }
    if y_prob is not None and y_prob.shape[1] > 1:
        try:
            res["roc_auc"] = roc_auc_score(y_true, y_prob, multi_class="ovr")
        except ValueError:
            pass
    return res


def eval_multiclass(y_true, y_pred, y_prob=None):
    """Multi-class metrics."""
    res = {
        "acc": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "kappa": cohen_kappa_score(y_true, y_pred),
    }
    return res
