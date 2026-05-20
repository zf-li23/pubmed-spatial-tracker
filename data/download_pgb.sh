mkdir -p data/pgb && cd data/pgb

# 下载主压缩包（~2 GB）
wget -c https://zenodo.org/records/6406776/files/pgb_part1.zip

# 解压
unzip pgb_part1.zip

# 解压后检查生成的文件（应该包括 pgb_0.zip ~ pgb_9.zip 等十个小分卷）
ls -lh pgb_*.zip

# 将所有小分卷解压到一个统一目录，排除主压缩包
mkdir -p extracted && for zip in pgb_[0-9].zip; do unzip "$zip" -d extracted/ && rm "$zip"; done