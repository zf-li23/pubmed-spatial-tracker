# 1. 安装 kagglehub（建议在 Python 虚拟环境里安装）
pip install kagglehub

# 2. Python 下载脚本 — 直接将文件复制到 data/PubMed-MultiLabel/
TARGET_DIR="$(cd "$(dirname "$0")" && pwd)/PubMed-MultiLabel"
mkdir -p "$TARGET_DIR"
export TARGET_DIR

python -c "
import kagglehub, shutil, os
path = kagglehub.dataset_download('owaiskhan9654/pubmed-multilabel-text-classification')
print('Dataset downloaded to cache:', path)

target = os.environ['TARGET_DIR']
for fname in os.listdir(path):
    shutil.copy2(os.path.join(path, fname), os.path.join(target, fname))
    print(f'  Copied {fname}')
print('Done. Files are in:', target)
"