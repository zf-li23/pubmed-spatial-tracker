import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/frontend/src/App.jsx", "r") as f:
    text = f.read()

# Update Table Headers
old_thead = """                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider">大类(预测)</th>
                      <th className="px-3 py-2.5 text-center text-gray-600 font-bold tracking-wider">PDF</th>"""
new_thead = """                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider">大类(预测)</th>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider w-[10rem]">Tag(预测)</th>
                      <th className="px-3 py-2.5 text-center text-gray-600 font-bold tracking-wider">本地 PDF</th>
                      <th className="px-3 py-2.5 text-center text-gray-600 font-bold tracking-wider">URL 外链</th>"""
if old_thead in text:
    text = text.replace(old_thead, new_thead)


# Update Table Rows
old_trow = """                          <td className="px-3 py-2.5 flex items-center">
                             <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                row.category==='Review'?'bg-yellow-200 text-yellow-800':
                                row.category==='Technology'?'bg-purple-200 text-purple-800':
                                row.category==='Research'?'bg-green-200 text-green-800':
                                'bg-blue-200 text-blue-800'}`}>
                                {row.category}
                             </span>
                             {row.auto_predicted_category && row.auto_predicted_category !== row.category && (
                                <span className="ml-1 text-[10px] text-gray-400" title={`原始预测: ${row.auto_predicted_category}`}>🔧</span>
                             )}
                          </td>
                          <td className="px-3 py-2.5 text-center">
                             {row.pdf_path ? (
                                row.pdf_path.startsWith('http') ?
                                   <a href={row.pdf_path} target="_blank" rel="noreferrer" className="text-teal-600 underline font-bold px-2 whitespace-nowrap" onClick={e=>e.stopPropagation()}>🔗 外链</a> :
                                   <a href={`/pdf?path=${encodeURIComponent(row.pdf_path)}`} target="_blank" rel="noreferrer" className="text-blue-600 underline font-bold px-2 whitespace-nowrap" onClick={e=>e.stopPropagation()}>👁 查看</a>
                             ) : <span className="text-gray-300">-</span>}
                          </td>"""

new_trow = """                          <td className="px-3 py-2.5">
                             <div className="flex items-center">
                                 <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                    row.category==='Review'?'bg-yellow-200 text-yellow-800':
                                    row.category==='Technology'?'bg-purple-200 text-purple-800':
                                    row.category==='Research'?'bg-green-200 text-green-800':
                                    'bg-blue-200 text-blue-800'}`}>
                                    {row.category}
                                 </span>
                                 {row.auto_predicted_category && row.auto_predicted_category !== row.category && (
                                    <span className="ml-1 text-[10px] text-gray-400" title={`原始预测: ${row.auto_predicted_category}`}>🔧</span>
                                 )}
                             </div>
                          </td>
                          <td className="px-3 py-2.5">
                             <div className="flex items-center truncate max-w-[10rem] text-xs text-gray-600" title={row.tags}>
                                {row.tags || <span className="text-gray-300 italic">未打标签</span>}
                                {row.auto_predicted_tags && row.auto_predicted_tags !== row.tags && (
                                   <span className="ml-1 text-[10px] text-gray-400" title={`原始预测: ${row.auto_predicted_tags}`}>🔧</span>
                                )}
                             </div>
                          </td>
                          <td className="px-3 py-2.5 text-center">
                             {row.pdf_path && !row.pdf_path.startsWith('http') ? <a href={`/pdf?path=${encodeURIComponent(row.pdf_path)}`} target="_blank" rel="noreferrer" className="text-blue-600 underline font-bold px-2 whitespace-nowrap" onClick={e=>e.stopPropagation()}>👁 查看</a> : <span className="text-gray-300">-</span>}
                          </td>
                          <td className="px-3 py-2.5 text-center">
                             {(row.url || (row.pdf_path && row.pdf_path.startsWith('http'))) ? <a href={row.url || row.pdf_path} target="_blank" rel="noreferrer" className="text-teal-600 underline font-bold px-2 whitespace-nowrap" onClick={e=>e.stopPropagation()}>🔗 外链</a> : <span className="text-gray-300">-</span>}
                          </td>"""

if old_trow in text:
    text = text.replace(old_trow, new_trow)
else:
    print("Could not find old_trow")

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/frontend/src/App.jsx", "w") as f:
    f.write(text)
print("App.jsx fixed")
