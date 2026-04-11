import { useState, useEffect } from 'react';

const CATEGORIES = ["Review", "Technology", "Database", "Data Analysis", "Research"];

export default function AnnotationForm({ row, onUpdateContent, storedTags, updateStoredTags }) {
  const [cat, setCat] = useState("");
  const [tags, setTags] = useState([]);
  const [customTagGeneral, setCustomTagGeneral] = useState("");
  const [newGroupTagInputs, setNewGroupTagInputs] = useState({ metaCategory: "", domain: "", technology: "", analysis: "" });
  const [pdfUrl, setPdfUrl] = useState("");
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
     const defaultCat = row.category || row.auto_predicted_category || row.naive_category || "Research";
     const defaultTagsStr = row.tags || row.auto_predicted_tags || row.naive_tags || "";
     setCat(defaultCat);
     setTags(defaultTagsStr ? defaultTagsStr.split(';').map(t=>t.trim()).filter(Boolean) : []);
  }, [row.pmid, row.category, row.auto_predicted_category, row.naive_category, row.tags, row.auto_predicted_tags, row.naive_tags]);

  const toggleTag = (t) => {
     if(tags.includes(t)) setTags(tags.filter(x=>x!==t));
     else setTags([...tags, t]);
  };

  const handleAddGeneralCustomTag = (e) => {
     e.preventDefault();
     const tInput = customTagGeneral.trim();
     if(tInput && !tags.includes(tInput)) {
        setTags([...tags, tInput]);
     }
     setCustomTagGeneral("");
  };

  const handleAddGroupTag = (e, groupKey) => {
     e.preventDefault();
     const newVal = newGroupTagInputs[groupKey].trim();
     if(newVal && !storedTags[groupKey].includes(newVal)) {
        const updated = {...storedTags};
        updated[groupKey] = [...updated[groupKey], newVal];
        updateStoredTags(updated);
        if(!tags.includes(newVal)) setTags([...tags, newVal]);
     }
     setNewGroupTagInputs({...newGroupTagInputs, [groupKey]: ""});
  };

  const saveBasicAnnotation = () => {
     setUploading(true);
     const finalTags = tags.filter(t => !["聚类","去卷积","缺失值插补","细胞通讯"].includes(t));
     const joinedTags = finalTags.join("; ");

     fetch(`/api/articles/${row.pmid}/annotate`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ category: cat, tags: joinedTags })
     })
       .then(res => res.json())
       .then(data => {
          setUploading(false);
          if (data.detail) {
            alert("提交失败: " + JSON.stringify(data));
            return;
          }
          onUpdateContent({ ...row, category: cat, tags: joinedTags, is_manually_confirmed: true });
       })
       .catch(err => {
          setUploading(false);
          console.error("Annotate fail:", err);
          alert("提交失败");
       });
  };

  const handleFileUpload = (file) => {
     if(!file) return;
     if(!pdfUrl) {
         alert("请先在上方的输入框填入文献的 URL 链接，然后再拖拽或选择本地 PDF 上传！");
         return;
     }

     setUploading(true);
     const finalTags = tags.filter(t => !["聚类","去卷积","缺失值插补","细胞 通讯"].includes(t));
     const joinedTags = finalTags.join("; ");
     
     const fd = new FormData();
     fd.append("file", file);
     fd.append("category", cat);
     fd.append("tags", joinedTags);
     fd.append("doi", row.doi || row.pmid);
     fd.append("pub_year", row.pub_year || "Unknown");
     fd.append("url", pdfUrl);

     // 在上传时不要直接跳转走，先保留在当前页并给出加载提示
     // 更新部分状态，但不包含会引起跳转的完整乐观数据
     onUpdateContent({ ...row, pdf_path: "(上传中...)" });

     fetch(`/api/articles/${row.pmid}/pdf/upload`, {
        method: "POST",
        body: fd
     }).then(res => res.json()).then(res => {
        setUploading(false);
        if(res.db_path){
           console.log("PDF 归档成功", res.db_path);
           // 上传成功后再发送真实的数据更新，使其产生自然的跳转与查看按钮显示
           onUpdateContent({ ...row, category: cat, tags: joinedTags, is_manually_confirmed: true, url: pdfUrl, pdf_path: res.db_path });
        } else {
           alert("上传失败！" + JSON.stringify(res));
           onUpdateContent({ ...row, pdf_path: null }); // 回滚状态
        }
     }).catch(err => {
         setUploading(false);
         console.error("Upload error:", err);
         alert("上传失败");
     });
  };

  const onUrlSubmit = (e) => {
     e.preventDefault();
     if(!pdfUrl) return;
     setUploading(true);
     const finalTags = tags.filter(t => !["聚类","去卷积","缺失值插补","细胞通讯"].includes(t));
     const joinedTags = finalTags.join("; ");

     // 保留在当前页，提供加载态
     onUpdateContent({ ...row, pdf_path: "(后台爬取中...)" });

     fetch(`/api/articles/${row.pmid}/pdf/url`, {
         method: "POST",
         headers: {"Content-Type": "application/json"},
         body: JSON.stringify({
             url: pdfUrl,
             category: cat,
             tags: joinedTags,
             doi: row.doi || row.pmid,
             pub_year: row.pub_year || "Unknown"
         })
     }).then(res => res.json()).then(data => {
         setUploading(false);
         if(data.db_path) {
             console.log("爬取完成", data.db_path);
             onUpdateContent({ ...row, category: cat, tags: joinedTags, is_manually_confirmed: true, url: pdfUrl, pdf_path: data.db_path });
         }
         else {
             console.error(data.detail);
             alert("爬取失败！" + JSON.stringify(data));
             onUpdateContent({ ...row, pdf_path: null });
         }
     }).catch(err => {
         setUploading(false);
         console.error("URL err", err);
         alert("爬取失败");
     });
  };

  const onSaveUrlOnly = (e) => {
     e.preventDefault();
     if(!pdfUrl) return;
     setUploading(true);
     const finalTags = tags.filter(t => !["聚类","去卷积","缺失值插补","细胞通讯"].includes(t));
     const joinedTags = finalTags.join("; ");

     fetch(`/api/articles/${row.pmid}/pdf/save_link`, {
         method: "POST",
         headers: {"Content-Type": "application/json"},
         body: JSON.stringify({
             url: pdfUrl,
             category: cat,
             tags: joinedTags
         })
     }).then(res => res.json()).then(data => {
         setUploading(false);
         if(data.path) {
             console.log("仅保存外链成功", data.path);
             onUpdateContent({ ...row, category: cat, tags: joinedTags, is_manually_confirmed: true, url: pdfUrl });
         } else {
             console.error(data.detail);
             alert("保存外链失败: " + JSON.stringify(data));
         }
     }).catch(err => {
         setUploading(false);
         console.error("Link err", err);
         alert("保存外链失败");
     });
  };

  const renderTagGroup = (title, groupKey, items) => (
     <div className="mb-3">
         <div className="text-xs font-bold text-gray-500 mb-1">{title}</div>
         <div className="flex flex-wrap gap-1.5 mb-1.5 text-xs">
            {items.map(t => (
               <button key={t} onClick={()=>toggleTag(t)} className={`px-2 py-1 rounded border transition-all font-semibold ${tags.includes(t) ? 'bg-indigo-600 text-white shadow-sm border-indigo-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'}`}>
                 {t}
               </button>
            ))}
         </div>
         {groupKey !== "metaCategory" && (
            <form onSubmit={(e)=>handleAddGroupTag(e, groupKey)} className="flex mt-1">
               <input type="text" placeholder={`Add new ${title}...`} className="text-xs flex-1 border border-gray-300 px-2 py-1 rounded-l outline-none focus:ring-1 focus:ring-blue-200" value={newGroupTagInputs[groupKey]} onChange={e=>setNewGroupTagInputs({...newGroupTagInputs, [groupKey]: e.target.value})} />
               <button type="submit" className="bg-gray-600 hover:bg-gray-700 text-white px-2 py-1 rounded-r text-xs transition-colors">Add</button>
            </form>
         )}
     </div>
  );

  return (
    <div className="p-6 space-y-6">
       <div>
         <div className="text-xs text-gray-500 mb-1 flex justify-between">
            <span>{row.journal} • {row.pub_year}</span>
            {row.doi && <a href={`https://doi.org/${row.doi}`} target="_blank" rel="noreferrer" className="text-blue-600 underline font-bold">文献传送门链接➚</a>}
         </div>
         <h2 className="text-lg font-bold text-gray-900 leading-snug">{row.title}</h2>
       </div>

       <div>
          <h3 className="font-semibold text-gray-700 mb-1 border-b pb-1">摘要 (Abstract)</h3>
          <div className="text-xs text-gray-600 h-[18vh] overflow-y-auto bg-gray-50 border p-3 rounded leading-relaxed shadow-inner">
            {row.abstract || "无可用摘要。"}
          </div>
       </div>
       
       <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
           <h3 className="font-bold text-gray-800 mb-3 text-sm flex items-center">
             <span className="bg-blue-600 text-white rounded-full w-5 h-5 inline-flex items-center justify-center mr-2">1</span> 
             分类修证 (Category)
           </h3>
           <div className="flex flex-wrap gap-2 text-sm mb-4">
             {CATEGORIES.map(c => (
                <label key={c} className={`cursor-pointer px-3 py-1 rounded-full border transition-all ${cat===c ? 'bg-blue-600 text-white shadow-md border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'}`}>
                  <input type="radio" value={c} checked={cat===c} onChange={()=>setCat(c)} className="hidden" />
                  {c}
                </label>
             ))}
           </div>
           
           <h3 className="font-bold text-gray-800 mt-4 mb-2 text-sm flex items-center">
             <span className="bg-blue-600 text-white rounded-full w-5 h-5 inline-flex items-center justify-center mr-2">2</span> 
             标签添加 (Tags)
           </h3>
           
           <div className="mb-4">
              {cat === 'Review' && (
                 <>
                    {renderTagGroup("Meta-Category (大类)", "metaCategory", storedTags.metaCategory)}
                    {renderTagGroup("Domain (领域)", "domain", storedTags.domain)}
                 </>
              )}
              {cat === 'Technology' && renderTagGroup("Technology (Technology名)", "technology", storedTags.technology)}
              {cat === 'Data Analysis' && renderTagGroup("Analysis (分析类)", "analysis", storedTags.analysis)}
              {cat === 'Research' && (
                 <>
                    {renderTagGroup("Domain (领域)", "domain", storedTags.domain)}
                    {renderTagGroup("Technology (Technology名)", "technology", storedTags.technology)}
                 </>
              )}
              {cat === 'Database' && (
                 <div className="text-xs text-gray-500 mb-2">Database无专属分类群，请在下方自由添加新Tag。</div>
              )}
           </div>

           <div className="mb-3 pt-2 border-t border-gray-200">
              <div className="text-xs font-bold text-gray-600 mb-1">当前所选 Tags 预览:</div>
              <div className="flex flex-wrap gap-1 text-xs mb-2">
                 {tags.map(t=>(
                    <span key={t} className="px-2 py-1 rounded border bg-indigo-600 text-white border-indigo-600 flex items-center gap-1 font-semibold">
                       {t} 
                       <span onClick={()=>toggleTag(t)} className="cursor-pointer ml-1 hover:text-red-200">×</span>
                    </span>
                 ))}
                 {tags.length === 0 && <span className="text-gray-400 italic">None</span>}
              </div>
              <form onSubmit={handleAddGeneralCustomTag} className="flex">
                 <input type="text" placeholder="自由命名额外 Custom Tag..." className="text-xs flex-1 border border-gray-300 px-2 py-1.5 rounded-l outline-none focus:ring-1 focus:ring-blue-200" value={customTagGeneral} onChange={e=>setCustomTagGeneral(e.target.value)} />
                 <button type="submit" className="bg-gray-800 hover:bg-gray-900 text-white px-3 py-1.5 rounded-r text-xs transition-colors">附加</button>
              </form>
           </div>
           
           <button onClick={saveBasicAnnotation} disabled={uploading} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2.5 rounded font-bold shadow-md transition-colors flex justify-center items-center gap-2 mt-4">
              {uploading ? '处理中...' : '💾 仅提交标注（无全文PDF）'}
           </button>
       </div>

       <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 shadow-sm relative">
           <h3 className="font-bold text-gray-800 mb-3 text-sm flex items-center">
             <span className="bg-amber-500 text-white rounded-full w-5 h-5 inline-flex items-center justify-center mr-2">3</span> 
             PDF 离线归档并确认 (Upload File)
           </h3>
           
           <form onSubmit={onUrlSubmit} className="flex mb-4 shadow-sm">
              <input type="text" placeholder="直链投喂 或 仅留存URL..." className="text-sm flex-1 border border-gray-300 px-3 py-1.5 rounded-l outline-none focus:ring-2 focus:ring-blue-200" value={pdfUrl} onChange={e=>setPdfUrl(e.target.value)} />
              <button type="submit" disabled={uploading} className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 text-sm transition-colors border-r border-blue-700">
                📥 爬链接
              </button>
              <button type="button" onClick={onSaveUrlOnly} disabled={uploading} className="bg-teal-500 hover:bg-teal-600 text-white px-3 py-1.5 text-sm rounded-r transition-colors">
                🔗 仅存链接
              </button>
           </form>

           <div className="relative">
              <div 
                 onDragOver={(e)=>{e.preventDefault(); e.currentTarget.classList.add('bg-blue-100', 'border-blue-400')}} 
                 onDragLeave={(e)=>e.currentTarget.classList.remove('bg-blue-100', 'border-blue-400')}
                 onDrop={(e)=>{
                     e.preventDefault();
                     e.currentTarget.classList.remove('bg-blue-100', 'border-blue-400');
                     if(e.dataTransfer.files && e.dataTransfer.files[0]) {
                        handleFileUpload(e.dataTransfer.files[0]);
                     }
                 }}
                 className="border-2 border-dashed border-blue-300 rounded-lg p-6 bg-white transition-all flex flex-col items-center justify-center cursor-pointer shadow-sm group"
              >
                 <input type="file" accept="application/pdf" className="absolute inset-0 w-full h-[60%] opacity-0 cursor-pointer z-10" onChange={(e)=>{if(e.target.files[0]) handleFileUpload(e.target.files[0])}} />
                 <svg className="w-8 h-8 text-blue-400 mb-2 group-hover:text-blue-500 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v9m0-9l-3 3m3-3l3 3"></path></svg>
                 <span className="text-blue-600 font-bold mb-1">点此选择 或 拖拽本地文件至此</span>
                 <span className="text-gray-500 text-xs mt-1 text-center leading-tight max-w-[80%]">系统将根据 "分类(Category)" 与 "年份_Tag_DOI" 在 PDF_Archive 里实现归档</span>
              </div>
           </div>
       </div>
    </div>
  );
}
