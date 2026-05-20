# 1. 创建并进入数据目录
mkdir -p data/ohsumed && cd data/ohsumed

# 2. 下载所有分卷文件（基础URL + 各自文件名）
base_url="https://trec.nist.gov/data/filtering"
for part in ohsumed88 ohsumed89 ohsumed90 ohsumed91; do
    wget -c "${base_url}/t9.${part}.tar.gz"
done

# 3. 合并分卷（分卷解压后需按官方说明合并：将 ohsumed.88、ohsumed.89、ohsumed.90、ohsumed.91 合并成一个文件）
# 这一步最好参考解压后得到的 README 或官方说明，标准做法是：
# 解压各分卷到同一目录 → 将各个 ohsumed.年份 文件按顺序合并为一个统一的 ohsumed.all
# 示例：
for part in ohsumed88 ohsumed89 ohsumed90 ohsumed91; do
    tar -xzf t9.${part}.tar.gz
done
# 合并前请先 ls 确认解出的文件命名（可能是 ohsumed.88 ohsumed.89 ...）
cat ohsumed.88 ohsumed.89 ohsumed.90 ohsumed.91 > ohsumed.all