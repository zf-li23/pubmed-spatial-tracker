import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import numpy as np
import torch
from tqdm import tqdm
from transformers import BertTokenizer, BertModel
from ..config import BIOBERT_MODEL


class BioBERTExtractor:
    def __init__(self, model_name=BIOBERT_MODEL, device=None, batch_size=32):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def _embed(self, texts):
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
        enc = {k: v.to(self.device) for k, v in enc.items()}
        with torch.no_grad():
            out = self.model(**enc)
        mask = enc["attention_mask"].unsqueeze(-1).float()
        emb = (out.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1)
        return emb.cpu().numpy()

    def fit(self, texts):
        return self

    def transform(self, texts):
        all_embs = []
        for i in tqdm(range(0, len(texts), self.batch_size), desc="BioBERT", unit="batch",
                      leave=False):
            batch = texts[i:i + self.batch_size]
            all_embs.append(self._embed(batch))
        return np.vstack(all_embs)

    def fit_transform(self, texts):
        return self.transform(texts)
