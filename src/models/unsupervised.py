from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score


def cluster_lda(lda_features, n_clusters, true_labels=None):
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    pred = km.fit_predict(lda_features)
    res = {}
    if true_labels is not None:
        res["nmi"] = normalized_mutual_info_score(true_labels, pred)
        res["ari"] = adjusted_rand_score(true_labels, pred)
    return pred, res
