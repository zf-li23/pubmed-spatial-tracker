"""Graph models: GCN, GraphSAGE for PGB citation graph."""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


class GCN(nn.Module):
    """2-layer Graph Convolutional Network."""

    def __init__(self, in_dim, hidden_dim, out_dim):
        super().__init__()
        self.conv1 = nn.Linear(in_dim, hidden_dim)
        self.conv2 = nn.Linear(hidden_dim, out_dim)

    def forward(self, x, adj):
        x = F.relu(self.conv1(torch.spmm(adj, x)))
        x = self.conv2(torch.spmm(adj, x))
        return x


class GraphSAGE(nn.Module):
    """2-layer GraphSAGE with mean aggregator."""

    def __init__(self, in_dim, hidden_dim, out_dim):
        super().__init__()
        self.w1 = nn.Linear(in_dim * 2, hidden_dim)
        self.w2 = nn.Linear(hidden_dim * 2, out_dim)

    def _aggregate(self, x, adj, n):
        """Mean-pool neighbor features."""
        aggr = torch.zeros_like(x)
        for i in range(n):
            nbrs = adj[i] if isinstance(adj, list) else adj[i].nonzero().squeeze(1)
            if len(nbrs) > 0:
                aggr[i] = x[nbrs].mean(dim=0)
        return aggr

    def forward(self, x, adj):
        n = x.size(0)
        h1 = F.relu(self.w1(torch.cat([x, self._aggregate(x, adj, n)], dim=1)))
        h2 = self.w2(torch.cat([h1, self._aggregate(h1, adj, n)], dim=1))
        return h2


class GraphClassifier:
    """Wrapper for GCN / GraphSAGE with sklearn-like interface.

    Parameters
    ----------
    model_type : str, "gcn" or "graphsage"
    in_dim : int
    hidden_dim : int, default 64
    n_classes : int
    lr : float, default 0.01
    epochs : int, default 200
    device : str or None
    """

    def __init__(self, model_type, in_dim, n_classes, hidden_dim=64,
                 lr=0.01, epochs=200, device=None):
        self.model_type = model_type
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.n_classes = n_classes
        self.lr = lr
        self.epochs = epochs
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._build_model()

    def _build_model(self):
        if self.model_type == "gcn":
            self.model = GCN(self.in_dim, self.hidden_dim, self.n_classes)
        elif self.model_type == "graphsage":
            self.model = GraphSAGE(self.in_dim, self.hidden_dim, self.n_classes)
        else:
            raise ValueError(f"Unknown model_type: {self.model_type}")
        self.model.to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.lr)

    def fit(self, X, y, adj, train_idx):
        """Train on a single train/test split.

        Parameters
        ----------
        X : np.ndarray, node features (n_nodes, in_dim)
        y : np.ndarray, labels (n_nodes,)
        adj : list of lists or sparse matrix
        train_idx : np.ndarray, training indices
        """
        y_t = torch.LongTensor(y).to(self.device)
        X_t = torch.FloatTensor(X).to(self.device)
        self.model.train()
        for ep in range(self.epochs):
            self.optimizer.zero_grad()
            out = self.model(X_t, adj)
            loss = F.cross_entropy(out[train_idx], y_t[train_idx])
            loss.backward()
            self.optimizer.step()

    def predict(self, X, adj, test_idx):
        """Predict on test indices."""
        self.model.eval()
        with torch.no_grad():
            X_t = torch.FloatTensor(X).to(self.device)
            logits = self.model(X_t, adj)
            pred = logits[test_idx].argmax(dim=1).cpu().numpy()
        return pred


MODELS = {
    "gcn": lambda in_dim, n_classes, **kw: GraphClassifier("gcn", in_dim, n_classes, **kw),
    "graphsage": lambda in_dim, n_classes, **kw: GraphClassifier("graphsage", in_dim, n_classes, **kw),
}
