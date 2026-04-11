import { useState, useEffect, useMemo } from 'react';
import AnnotationForm from './components/AnnotationForm';
import TagManager from './components/TagManager';

const CATEGORIES = ["Review", "Technology", "Database", "Data Analysis", "Research"];

const DEFAULT_TAG_DICT = {
  metaCategory: ["General", "Technology", "Database", "Data Analysis"],
  domain: ["Neuroscience", "Development", "Cancer", "Reproduction"],
  technology: ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", "CosMx"],
  analysis: ["Clustering", "Deconvolution", "Imputation", "Cell Communication", "Spatial Trajectory"]
};

function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [filterCategory, setFilterCategory] = useState("");
  const [filterConfirmed, setFilterConfirmed] = useState("all");
    
  
  const [filterPmid, setFilterPmid] = useState("");
  const [isTagManagerOpen, setIsTagManagerOpen] = useState(false);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 30; // Control pagination limit
  
  const [selectedRow, setSelectedRow] = useState(null);
  
  const [storedTags, setStoredTags] = useState(DEFAULT_TAG_DICT);

  useEffect(() => {
      fetch('/api/tags')
      .then(res => res.json())
      .then(data => setStoredTags(data))
      .catch(err => console.error("Failed to load tags", err));
  }, []);

  const updateStoredTags = (newDict) => {
     setStoredTags(newDict);
       fetch('/api/tags', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(newDict)
     }).catch(err => console.error("Failed to save tags", err));
  };

  const loadData = () => {
    setLoading(true);
    fetch("/api/articles")
      .then(res => res.json())
      .then(result => {
         setData(result);
         
         // Removed batch logic
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const filteredData = useMemo(() => {
    return data.filter(item => {
       if (filterPmid && !String(item.pmid).includes(filterPmid.trim())) return false;
       if (filterCategory && item.category !== filterCategory) return false;
       if (filterConfirmed === 'yes' && !item.is_manually_confirmed) return false;
       if (filterConfirmed === 'no' && item.is_manually_confirmed) return false;
       return true;
    });
  }, [data, filterCategory, filterConfirmed, filterPmid]);

  

  // Reset pagination when filters change
  useEffect(() => {
     setCurrentPage(1);
  }, [filterCategory, filterConfirmed, filterPmid]);

  // Calculate current page data
  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = useMemo(() => {
     const start = (currentPage - 1) * itemsPerPage;
     return filteredData.slice(start, start + itemsPerPage);
  }, [filteredData, currentPage, itemsPerPage]);

  const handleNextRow = (currentPmid) => {
     const currentIndex = filteredData.findIndex(r => r.pmid === currentPmid);
     if (currentIndex !== -1 && currentIndex + 1 < filteredData.length) {
         const nextRow = filteredData[currentIndex + 1];
         setSelectedRow(nextRow);
         
         // Only change page if the next row is on a different page
         const nextPage = Math.floor((currentIndex + 1) / itemsPerPage) + 1;
         if (nextPage !== currentPage) {
             setCurrentPage(nextPage);
         }
     } else {
         setSelectedRow(null);
     }
  };

  const handleDiscard = (pmid) => {
     if(!confirm("确认打上废弃(Discarded)标签并将其留用作负样本数据吗？")) return;
     
     // 乐观更新为废弃状态
     setData(prev => prev.map(r => {
        if(r.pmid === pmid) {
           const newTags = r.tags ? `${r.tags}; Discarded` : "Discarded";
           return { ...r, tags: newTags, is_manually_confirmed: true };
        }
        return r;
     }));
     
     handleNextRow(pmid);
     
     fetch(`/api/articles/${pmid}/discard`, { method: "POST" }).catch(err => {
         console.error("Discard failed", err);
         // silent error for better UX
     });
  };

  const handleUpdateContent = (updatedRow) => {
     // Optimistically update the specific row
     setData(prev => prev.map(r => r.pmid === updatedRow.pmid ? updatedRow : r));
     handleNextRow(updatedRow.pmid);
  };

  const handlePmidUpload = (e) => {
     const file = e.target.files[0];
     if(!file) return;
     const fd = new FormData();
     fd.append("file", file);
     setLoading(true);
     fetch("/api/pmids/upload", { method: "POST", body: fd })
       .then(res => res.json())
       .then(data => {
           alert(data.message || data.detail);
           if(!data.detail) {
               setFilterPmid(""); // Reset filter so they can search
               setFilterConfirmed("all");
               loadData();
           }
       })
       .catch(err => {
           alert("导入出错: " + err);
       })
       .finally(() => {
           e.target.value = null; // reset input
           setLoading(false);
       });
  };

  const triggerActiveLearning = () => {
      fetch("/api/ml/active_learning", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            if(data.error) alert("Error: " + data.error);
            else if(data.detail) alert("Detail: " + data.detail);
            else {
                alert(data.message);
                if(data.status === "success") {
                    
                    setFilterConfirmed("all");
                    loadData(); // Resync updated ML rows
                }
            }
        }).catch(err => {
            alert("训练请求失败，请检查终端并确认安装 scikit-learn！");
        });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      <div className="w-2/3 flex flex-col border-r border-gray-300 bg-white">
         <div className="p-4 border-b flex justify-between items-center bg-gray-50 flex-wrap gap-2">
            <h1 className="text-xl font-bold text-gray-800">PubMed 空间标注流 (v3.0)</h1>
            <div className="flex space-x-2 items-center flex-wrap">
               <input 
                 type="text" 
                 placeholder="🔍 搜索 PMID..." 
                 value={filterPmid} 
                 onChange={e=>setFilterPmid(e.target.value)} 
                 className="border border-gray-300 rounded px-2 py-1.5 text-sm bg-white outline-none focus:ring-2 focus:ring-blue-300 w-32"
               />
               
               <select className="border border-gray-300 rounded px-2 py-1.5 text-sm bg-white" value={filterCategory} onChange={e=>setFilterCategory(e.target.value)}>
                 <option value="">所有分类</option>
                 {CATEGORIES.map(c=><option key={c} value={c}>{c}</option>)}
               </select>
               <select className="border border-gray-300 rounded px-2 py-1.5 text-sm bg-white" value={filterConfirmed} onChange={e=>setFilterConfirmed(e.target.value)}>
                 <option value="all">所有状态</option>
                 <option value="no">未标注</option>
                 <option value="yes">已标注确认</option>
               </select>
               <input type="file" id="pmid-upload" accept=".txt" className="hidden" onChange={handlePmidUpload} />
               <label htmlFor="pmid-upload" className="cursor-pointer bg-teal-500 text-white px-3 py-1.5 rounded text-sm font-semibold hover:bg-teal-600 transition-colors shadow-sm">
                 📤 导入 PMID 文件
               </label>
               <button onClick={loadData} className="bg-blue-500 text-white px-3 py-1.5 rounded text-sm font-semibold hover:bg-blue-600 transition-colors">刷新列表</button>
               <button onClick={()=>setIsTagManagerOpen(true)} className="bg-orange-500 text-white px-3 py-1.5 rounded text-sm font-semibold hover:bg-orange-600 transition-colors shadow-sm flex items-center gap-1">
                 🔖 管理 Tags
               </button>
               <button onClick={triggerActiveLearning} className="bg-purple-600 text-white px-3 py-1.5 rounded text-sm font-semibold hover:bg-purple-700 shadow-md transition-all flex items-center gap-1">
                 🚀 提交并让 AI 重新学习
               </button>
               <span className="ml-3 font-semibold text-gray-700 bg-white px-3 py-1.5 rounded shadow-sm border border-gray-200">
                  🔥 优先攻克顶部的疑难文献
               </span>
            </div>
         </div>
         
         <div className="flex-1 overflow-auto p-4">
            {loading ? <p className="text-gray-500 text-center mt-10">正在加载数据并构建视图...</p> : (
              <>
                <table className="min-w-full table-auto divide-y divide-gray-200 text-sm border-b">
                  <thead className="bg-[#f8fafc] sticky top-[-1rem] shadow-sm z-10">
                    <tr>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider">校验</th>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider" title="模型对该篇的预测困惑度，越高越需要人工介入">不确定性分数</th>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider w-1/3">标题</th>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider">年份</th>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider">大类</th>
                      <th className="px-3 py-2.5 text-left text-gray-600 font-bold tracking-wider w-[10rem]">Tag</th>
                      <th className="px-3 py-2.5 text-center text-gray-600 font-bold tracking-wider">本地 PDF</th>
                      <th className="px-3 py-2.5 text-center text-gray-600 font-bold tracking-wider">URL 外链</th>
                      <th className="px-3 py-2.5 text-center text-gray-600 font-bold tracking-wider">负样本标记</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {paginatedData.map((row) => (
                       <tr key={row.pmid} onClick={()=>setSelectedRow(row)} className={`cursor-pointer transition-colors ${selectedRow?.pmid === row.pmid ? 'bg-blue-100 hover:bg-blue-200' : 'hover:bg-blue-50'} ${((row.tags || '').includes('Discarded') || (row.auto_predicted_tags || '').includes('Discarded') || (row.naive_tags || '').includes('Discarded')) ? 'opacity-50 grayscale bg-gray-50' : ''}`}>
                          <td className="px-3 py-2.5 text-lg">{row.is_manually_confirmed ? '✅' : '⬜'}</td>
                          <td className="px-3 py-2.5 font-bold text-gray-500">{row.is_manually_confirmed ? "-" : (row.uncertainty_score ? Number(row.uncertainty_score).toFixed(3) : "-")}</td>
                          <td className="px-3 py-2.5 font-medium truncate max-w-[20rem]" title={row.title}>{row.title}</td>
                          <td className="px-3 py-2.5 text-gray-600">{row.pub_year}</td>
                          <td className="px-3 py-2.5">
                             <div className="flex items-center">
                                 <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                    row.category ? (row.category==='Review'?'bg-yellow-200 text-yellow-800' : row.category==='Technology'?'bg-purple-200 text-purple-800' : row.category==='Research'?'bg-green-200 text-green-800':'bg-blue-200 text-blue-800') : 
                                    row.auto_predicted_category ? (row.auto_predicted_category==='Review'?'bg-yellow-200 text-yellow-800' : row.auto_predicted_category==='Technology'?'bg-purple-200 text-purple-800' : row.auto_predicted_category==='Research'?'bg-green-200 text-green-800':'bg-blue-200 text-blue-800') :
                                    row.naive_category ? (row.naive_category==='Review'?'bg-yellow-200 text-yellow-800' : row.naive_category==='Technology'?'bg-purple-200 text-purple-800' : row.naive_category==='Research'?'bg-green-200 text-green-800':'bg-blue-200 text-blue-800') : 'bg-gray-50 text-gray-400'}`}>
                                    {row.category || row.auto_predicted_category || row.naive_category}
                                 </span>
                                 {(!row.category && !row.auto_predicted_category) && row.naive_category && (
                                    <span className="ml-1 text-[10px] text-gray-400" title={`Naive: ${row.naive_category}`}>🤖</span>
                                 )}
                                 {(!row.category) && row.auto_predicted_category && (
                                    <span className="ml-1 text-[10px] text-gray-400" title={`AI: ${row.auto_predicted_category}`}>🔧</span>
                                 )}
                             </div>
                          </td>
                          <td className="px-3 py-2.5">
                             <div className="flex items-center truncate max-w-[10rem] text-xs text-gray-600" title={row.tags}>
                                <span className="text-gray-800">
                                        {row.tags || row.auto_predicted_tags || row.naive_tags || <span className="text-gray-300 italic">未打标签</span>}
                                     </span>
                                     {(!row.tags && !row.auto_predicted_tags) && row.naive_tags && (
                                        <span className="ml-1 text-[10px] text-gray-400" title={`Naive: ${row.naive_tags}`}>🤖</span>
                                     )}
                                     {(!row.tags) && row.auto_predicted_tags && (
                                        <span className="ml-1 text-[10px] text-gray-400" title={`AI: ${row.auto_predicted_tags}`}>🔧</span>
                                     )}
                             </div>
                          </td>
                          <td className="px-3 py-2.5 text-center">
                             {row.pdf_path && !row.pdf_path.startsWith('http') ? <a href={`/pdf?path=${encodeURIComponent(row.pdf_path)}`} target="_blank" rel="noreferrer" className="text-blue-600 underline font-bold px-2 whitespace-nowrap" onClick={e=>e.stopPropagation()}>👁 查看</a> : <span className="text-gray-300">-</span>}
                          </td>
                          <td className="px-3 py-2.5 text-center">
                             {(row.url || (row.pdf_path && row.pdf_path.startsWith('http'))) ? <a href={row.url || row.pdf_path} target="_blank" rel="noreferrer" className="text-teal-600 underline font-bold px-2 whitespace-nowrap" onClick={e=>e.stopPropagation()}>🔗 外链</a> : <span className="text-gray-300">-</span>}
                          </td>
                          <td className="px-3 py-2.5 text-center">
                             <button onClick={(e)=>{e.stopPropagation(); handleDiscard(row.pmid);}} className="text-red-500 hover:text-white hover:bg-red-500 rounded px-2 py-1 transition-colors font-bold text-xs" title="打上伪数据标签">Discard</button>
                          </td>
                       </tr>
                    ))}
                    {paginatedData.length === 0 && (
                       <tr><td colSpan="6" className="text-center py-6 text-gray-500 italic">当前页无数据，请尝试更改筛选条件。</td></tr>
                    )}
                  </tbody>
                </table>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex justify-between items-center mt-4 bg-gray-50 p-2 rounded border border-gray-200">
                    <button 
                       onClick={() => setCurrentPage(p => Math.max(1, p - 1))} 
                       disabled={currentPage === 1}
                       className="px-3 py-1 bg-white border border-gray-300 rounded text-sm disabled:opacity-50 hover:bg-gray-100 transition-colors font-medium">
                       上一页
                    </button>
                    <span className="text-sm font-semibold text-gray-600">
                       Page {currentPage} of {totalPages} <span className="text-gray-400 font-normal ml-1">({filteredData.length} total articles)</span>
                    </span>
                    <button 
                       onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} 
                       disabled={currentPage === totalPages}
                       className="px-3 py-1 bg-white border border-gray-300 rounded text-sm disabled:opacity-50 hover:bg-gray-100 transition-colors font-medium">
                       下一页
                    </button>
                  </div>
                )}
              </>
            )}
         </div>
      </div>

      <div className="w-1/3 flex flex-col bg-white overflow-y-auto relative shadow-[0_0_10px_rgba(0,0,0,0.1)] border-l z-10">
         {selectedRow ? (
           <AnnotationForm 
             key={selectedRow.pmid}
             row={selectedRow} 
             onUpdateContent={handleUpdateContent}
             storedTags={storedTags}
             updateStoredTags={updateStoredTags}
           /> 
         ) : (
           <div className="flex items-center justify-center h-full text-gray-400 border-dashed border-2 border-gray-200 m-4 rounded">
              <span className="font-semibold text-lg italic tracking-wide">请在左侧表格单击行，开始阅读和标注</span>
           </div>
         )}
      </div>

      <TagManager 
         isOpen={isTagManagerOpen} 
         onClose={()=>setIsTagManagerOpen(false)}
         storedTags={storedTags}
         updateStoredTags={updateStoredTags}
         refreshData={loadData}
      />
    </div>
  );
}

export default App;
