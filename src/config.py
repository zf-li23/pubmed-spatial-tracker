"""Config."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

OHSUMED_PATH = DATA_DIR / "ohsumed" / "ohsumed.all"
PML_PATH = DATA_DIR / "PubMed-MultiLabel"
PGB_DIR = DATA_DIR / "pgb" / "extracted"

RANDOM_SEED = 42
CV_FOLDS = 5
TEST_SIZE = 0.2

TFIDF_MAX_FEAT = 5000
LDA_N_TOPICS = 15
BIOBERT_MODEL = "dmis-lab/biobert-base-cased-v1.1"
N2V_DIM = 128
