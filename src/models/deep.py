"""BioBERT + MLP fine-tuning wrapper."""

import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm
from transformers import BertTokenizer, BertModel
from ..config import BIOBERT_MODEL


class BioBERTMLP(nn.Module):
    def __init__(self, n_labels, hidden_dim=256):
        super().__init__()
        self.bert = BertModel.from_pretrained(BIOBERT_MODEL, local_files_only=True)
        self.classifier = nn.Sequential(
            nn.Linear(768, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, n_labels),
        )

    def forward(self, input_ids, attention_mask):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = out.last_hidden_state[:, 0, :]  # [CLS]
        return self.classifier(pooled)


class BioBERTFineTuner:
    def __init__(self, n_labels, lr=2e-5, epochs=3, batch_size=16, device=None,
                 multilabel=True):
        self.n_labels = n_labels
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.multilabel = multilabel
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizer.from_pretrained(BIOBERT_MODEL, local_files_only=True)
        self.model = BioBERTMLP(n_labels).to(self.device)
        if multilabel:
            self.criterion = nn.BCEWithLogitsLoss()
        else:
            self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=lr)

    def fit(self, texts, labels):
        dtype = torch.float32 if self.multilabel else torch.long
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
        ds = TensorDataset(enc["input_ids"], enc["attention_mask"],
                           torch.tensor(labels, dtype=dtype))
        dl = DataLoader(ds, batch_size=self.batch_size, shuffle=True)
        self.model.train()
        for ep in range(self.epochs):
            pbar = tqdm(dl, desc=f"  epoch {ep+1}/{self.epochs}",
                        unit="batch", leave=False)
            for ids, mask, lbl in pbar:
                ids, mask, lbl = ids.to(self.device), mask.to(self.device), lbl.to(self.device)
                self.optimizer.zero_grad()
                out = self.model(ids, mask)
                loss = self.criterion(out, lbl)
                loss.backward()
                self.optimizer.step()
                pbar.set_postfix(loss=loss.item())
        return self

    def predict(self, texts, batch_size=64):
        """Predict with batching to avoid OOM on large label spaces."""
        self.model.eval()
        all_preds = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = self.tokenizer(batch, padding=True, truncation=True,
                                 max_length=512, return_tensors="pt")
            with torch.no_grad():
                ids = enc["input_ids"].to(self.device)
                mask = enc["attention_mask"].to(self.device)
                logits = self.model(ids, mask)
            if self.multilabel:
                all_preds.append((torch.sigmoid(logits).cpu().numpy() > 0.5).astype(np.float32))
            else:
                all_preds.append(logits.argmax(dim=1).cpu().numpy())
        if self.multilabel:
            return np.vstack(all_preds)
        else:
            return np.concatenate(all_preds)

    def extract_embeddings(self, texts, batch_size=64):
        """Extract fine-tuned BioBERT [CLS] embeddings (768-dim)."""
        self.model.eval()
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = self.tokenizer(batch, padding=True, truncation=True,
                                 max_length=128, return_tensors="pt")
            with torch.no_grad():
                ids = enc["input_ids"].to(self.device)
                mask = enc["attention_mask"].to(self.device)
                out = self.model.bert(input_ids=ids, attention_mask=mask)
                cls = out.last_hidden_state[:, 0, :]  # [CLS]
                all_embs.append(cls.cpu().numpy())
        return np.vstack(all_embs)

    def predict_proba(self, texts, batch_size=64):
        """Predict probabilities with batching."""
        self.model.eval()
        all_probs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            enc = self.tokenizer(batch, padding=True, truncation=True,
                                 max_length=512, return_tensors="pt")
            with torch.no_grad():
                ids = enc["input_ids"].to(self.device)
                mask = enc["attention_mask"].to(self.device)
                logits = self.model(ids, mask)
            probs = torch.sigmoid(logits).cpu().numpy() if self.multilabel \
                else torch.softmax(logits, dim=1).cpu().numpy()
            all_probs.append(probs)
        return np.vstack(all_probs)
