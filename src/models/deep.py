"""BioBERT + MLP fine-tuning wrapper."""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModel
from ..config import BIOBERT_MODEL


class BioBERTMLP(nn.Module):
    def __init__(self, n_labels, hidden_dim=256):
        super().__init__()
        self.bert = AutoModel.from_pretrained(BIOBERT_MODEL)
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
    def __init__(self, n_labels, lr=2e-5, epochs=3, batch_size=16, device=None):
        self.n_labels = n_labels
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(BIOBERT_MODEL)
        self.model = BioBERTMLP(n_labels).to(self.device)
        self.criterion = nn.BCEWithLogitsLoss()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=lr)

    def fit(self, texts, labels):
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
        ds = TensorDataset(enc["input_ids"], enc["attention_mask"],
                           torch.tensor(labels, dtype=torch.float32))
        dl = DataLoader(ds, batch_size=self.batch_size, shuffle=True)
        self.model.train()
        for ep in range(self.epochs):
            for ids, mask, lbl in dl:
                ids, mask, lbl = ids.to(self.device), mask.to(self.device), lbl.to(self.device)
                self.optimizer.zero_grad()
                out = self.model(ids, mask)
                loss = self.criterion(out, lbl)
                loss.backward()
                self.optimizer.step()
        return self

    def predict(self, texts):
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
        self.model.eval()
        with torch.no_grad():
            ids, mask = enc["input_ids"].to(self.device), enc["attention_mask"].to(self.device)
            logits = self.model(ids, mask)
        return (torch.sigmoid(logits).cpu().numpy() > 0.5).astype(np.float32)

    def predict_proba(self, texts):
        enc = self.tokenizer(texts, padding=True, truncation=True,
                             max_length=512, return_tensors="pt")
        self.model.eval()
        with torch.no_grad():
            ids, mask = enc["input_ids"].to(self.device), enc["attention_mask"].to(self.device)
            logits = self.model(ids, mask)
        return torch.sigmoid(logits).cpu().numpy()
