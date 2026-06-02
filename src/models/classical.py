"""Classical ML models: NB, k-NN, SVM, LR."""

from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

MODELS = {
    "nb": lambda: GaussianNB(),
    "knn": lambda: KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
    "svm": lambda: SVC(kernel="rbf", probability=True, random_state=42),
    "lr": lambda: LogisticRegression(max_iter=1000, random_state=42, n_jobs=-1),
}
