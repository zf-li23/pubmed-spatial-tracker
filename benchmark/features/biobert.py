"""BioBERT sentence embedding extractor.

Uses mean pooling over last hidden layer.
"""

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from ..config import BIOBERT_MODEL


class BioBERTExtractor:
    def __init__(self, model_name=BIOBERT_MODEL, device=None, batch_size=32):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def _embed(self, texts):
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
        enc = {k: v.to(self.device) for k, v in enc.items()}
        with torch.no_grad():
            out = self.model(**enc)
        # mean pooling
        mask = enc["attention_mask"].unsqueeze(-1).float()
        emb = (out.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1)
        return emb.cpu().numpy()

    def fit(self, texts):
        return self  # no training needed

    def transform(self, texts):
        all_embs = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            all_embs.append(self._embed(batch))
        return np.vstack(all_embs)

    def fit_transform(self, texts):
        return self.transform(texts)
