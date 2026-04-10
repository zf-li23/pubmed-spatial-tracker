import re

with open("frontend/src/App.jsx", "r", encoding="utf-8") as f:
    text = f.read()

# Remove currentRound and filterBatch state
text = re.sub(r'const \[currentRound, setCurrentRound\] = useState\(.*?\);', '', text)
text = re.sub(r'const \[filterBatch, setFilterBatch\] = useState\("all"\);', '', text)

# Remove availableBatches useMemo
text = re.sub(r'// Derive unique batches\s*const availableBatches = useMemo\(\(\) => \{.*?\n\s*\}, \[data\]\);', '', text, flags=re.DOTALL)

# In loadData
load_data_old = """const unconfirmed = result.filter(r => r.is_manually_confirmed === false);
         if (unconfirmed.length > 0) {
             const minBatch = Math.min(...unconfirmed.map(r => parseInt(r.annotation_batch) || 999));
             setCurrentRound(minBatch);
         } else {
             setCurrentRound("已完成");
         }"""
load_data_new = """// Removed batch logic"""
text = text.replace(load_data_old, load_data_new)

# In filteredData
text = re.sub(r'if \(filterBatch !== \'all\' && String\(item\.annotation_batch\) !== filterBatch\) return false;\s*', '', text)
# Update dependency array
text = text.replace('], [data, filterCategory, filterConfirmed, filterBatch, filterPmid]);', '], [data, filterCategory, filterConfirmed, filterPmid]);')

# In useEffect for resetting pagination
text = text.replace('}, [filterCategory, filterConfirmed, filterBatch, filterPmid]);', '}, [filterCategory, filterConfirmed, filterPmid]);')

# triggerActiveLearning
text = text.replace('setFilterBatch(String(data.next_batch));', '')

# Remove batch select dropdown
select_batch = r'<select className="border border-gray-300 rounded px-2 py-1\.5 text-sm bg-white" value=\{filterBatch\} onChange=\{e=>setFilterBatch\(e\.target\.value\)\}>\s*<option value="all">所有批次</option>\s*\{availableBatches\.map\(b=><option key=\{b\} value=\{b\}>Batch \{b\}</option>\)\}\s*</select>'
text = re.sub(select_batch, '', text, flags=re.DOTALL)

# Update button text
text = text.replace('🚀 AI 本地学习并预测下批', '🚀 提交并让 AI 重新学习')

# Update right span text
text = text.replace('当前待标定轮次：【第 {currentRound} 轮】', '🔥 优先攻克顶部的疑难文献')

# Update table header
text = text.replace('<th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider">批次</th>', '<th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider" title="模型对该篇的预测困惑度，越高越需要人工介入">不确定性分数</th>')

# Update table body
text = text.replace('B{row.annotation_batch || 0}', '{row.is_manually_confirmed ? "-" : (row.uncertainty_score ? Number(row.uncertainty_score).toFixed(3) : "-")}')

with open("frontend/src/App.jsx", "w", encoding="utf-8") as f:
    f.write(text)
