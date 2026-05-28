"""Node2Vec embedding for PGB citation graph.

Generates paper-node embeddings via random walks on the citation graph.
These embeddings serve as the 4th feature representation for PGB,
enabling graph-aware classifiers (GCN, GraphSAGE, k-NN, SVM).
"""

import numpy as np
from pathlib import Path

N2V_DIM = 128  # embedding dimension
N2V_WALK_LEN = 20
N2V_NUM_WALKS = 10
N2V_P = 1.0   # return parameter
N2V_Q = 1.0   # in-out parameter


class Node2VecExtractor:
    """Generate Node2Vec embeddings for a PGB dataset.

    Requires the dataset to have called load_dataset(..., build_graph=True).
    """

    def __init__(self, dim=N2V_DIM, walk_length=N2V_WALK_LEN,
                 num_walks=N2V_NUM_WALKS, p=N2V_P, q=N2V_Q, seed=42):
        self.dim = dim
        self.walk_length = walk_length
        self.num_walks = num_walks
        self.p = p
        self.q = q
        self.seed = seed
        self._embeddings = None

    def fit(self, texts=None):
        return self

    def transform(self, texts=None):
        if self._embeddings is None:
            raise RuntimeError("Node2VecExtractor: call fit_transform() first "
                               "with a PGB dataset that has build_graph=True")
        return self._embeddings

    def fit_transform(self, texts=None, graph=None, n_nodes=None):
        """Generate embeddings from an adjacency-list graph.

        Parameters
        ----------
        graph : list[list[int]] or None
            Adjacency list. If None, attempts to use stored embeddings.
        n_nodes : int
            Number of nodes (must match len(graph)).

        Returns
        -------
        np.ndarray of shape (n_nodes, dim)
        """
        if graph is None:
            if self._embeddings is not None:
                return self._embeddings
            raise ValueError("Node2VecExtractor requires a graph (adjacency list).")

        if n_nodes is None:
            n_nodes = len(graph)

        self._embeddings = self._node2vec(graph, n_nodes)
        return self._embeddings

    def _node2vec(self, adj, n_nodes):
        """Core Node2Vec: biased random walks + SkipGram."""
        np.random.seed(self.seed)

        # Precompute alias tables for biased 2nd-order walks
        alias_nodes = self._precompute_alias_nodes(adj, n_nodes)

        # Generate walks
        walks = []
        nodes = np.arange(n_nodes)
        for _ in range(self.num_walks):
            np.random.shuffle(nodes)
            for start in nodes:
                if not adj[start]:
                    continue
                walk = [start]
                while len(walk) < self.walk_length:
                    cur = walk[-1]
                    if len(walk) == 1:
                        nxt = adj[cur][np.random.randint(0, len(adj[cur]))]
                    else:
                        prev = walk[-2]
                        nxt = self._alias_draw(
                            alias_nodes[(prev, cur)][0],
                            alias_nodes[(prev, cur)][1],
                            alias_nodes[(prev, cur)][2],
                        )
                    walk.append(nxt)
                walks.append([str(n) for n in walk])

        # SkipGram via Gensim (fallback to numpy-only if gensim unavailable)
        try:
            from gensim.models import Word2Vec
            model = Word2Vec(
                walks, vector_size=self.dim, window=5, min_count=1,
                sg=1, workers=4, epochs=5, seed=self.seed,
            )
            embeddings = np.zeros((n_nodes, self.dim), dtype=np.float64)
            for i in range(n_nodes):
                if str(i) in model.wv:
                    embeddings[i] = model.wv[str(i)]
            return embeddings
        except ImportError:
            # Fallback: simple SVD-based embedding (no gensim)
            return self._fallback_embed(adj, n_nodes)

    def _fallback_embed(self, adj, n_nodes):
        """Fallback: spectral embedding from adjacency (no gensim needed)."""
        from scipy import sparse
        from sklearn.decomposition import TruncatedSVD
        rows, cols, data = [], [], []
        for i, nbrs in enumerate(adj):
            for j in nbrs:
                rows.append(i); cols.append(j); data.append(1.0)
        A = sparse.csr_matrix((data, (rows, cols)), shape=(n_nodes, n_nodes))
        svd = TruncatedSVD(n_components=min(self.dim, n_nodes - 1), random_state=self.seed)
        return svd.fit_transform(A)

    def _precompute_alias_nodes(self, adj, n_nodes):
        """Precompute 1st-order alias tables (unweighted, uniform neighbors)."""
        alias = {}
        for src in range(n_nodes):
            nbrs = adj[src]
            if not nbrs:
                continue
            for dst in nbrs:
                # For each (src, dst) pair, compute biased transition probs
                probs = []
                for nxt in adj[dst]:
                    if nxt == src:
                        probs.append(1.0 / self.p)
                    elif nxt in adj[src]:
                        probs.append(1.0)
                    else:
                        probs.append(1.0 / self.q)
                total = sum(probs)
                if total > 0:
                    probs = [x / total for x in probs]
                else:
                    probs = [1.0 / len(probs)] * len(probs)
                alias[(src, dst)] = self._alias_setup(probs, adj[dst])
        return alias

    @staticmethod
    def _alias_setup(probs, items):
        """Build Vose's alias table for O(1) sampling."""
        n = len(probs)
        if n == 0:
            return (np.array([]), np.array([]), items)
        q = np.array(probs) * n
        J = np.zeros(n, dtype=int)
        smaller, larger = [], []
        for i, qi in enumerate(q):
            if qi < 1.0:
                smaller.append(i)
            else:
                larger.append(i)
        while smaller and larger:
            s = smaller.pop()
            l = larger.pop()
            J[s] = l
            q[l] = q[l] + q[s] - 1.0
            if q[l] < 1.0:
                smaller.append(l)
            else:
                larger.append(l)
        return q, J, items

    @staticmethod
    def _alias_draw(q, J, items=None):
        """Draw from alias table."""
        n = len(q)
        if n == 0:
            return 0
        k = np.random.randint(0, n)
        if np.random.rand() < q[k]:
            idx = k
        else:
            idx = J[k]
        return items[idx] if items is not None else idx
