import React, { useState } from 'react';
import { apiPath } from '../api';

export default function TagManager({ storedTags, updateStoredTags, isOpen, onClose, refreshData }) {
   if (!isOpen) return null;

   const [editingTag, setEditingTag] = useState(null);
   const [editValue, setEditValue] = useState("");
   const [loading, setLoading] = useState(false);

   const openEdit = (t, group) => {
      setEditingTag({ old: t, group });
      setEditValue(t);
   };

   const saveEdit = () => {
      if (!editValue.trim() || editValue === editingTag.old) {
          setEditingTag(null);
          return;
      }
      setLoading(true);
      fetch(apiPath('/api/tags/rename'), {
         method: 'PUT',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ old_tag: editingTag.old, new_tag: editValue })
      }).then(res => res.json()).then(() => {
         // update localStorage
         const newTags = { ...storedTags };
         newTags[editingTag.group] = newTags[editingTag.group].map(t => t === editingTag.old ? editValue : t);
         updateStoredTags(newTags);
         setEditingTag(null);
         refreshData(); // refresh table entries
         setLoading(false);
      }).catch(err => {
         console.error(err);
         alert("网络错误或后台崩溃");
         setLoading(false);
      });
   };

   const deleteTag = (t, group) => {
      if(!confirm(`⚠️ 警告: 您确定要彻底删除 "${t}" 吗？此操作将清洗所有被标记为该标签的行。`)) return;
      setLoading(true);
      fetch(apiPath('/api/tags/delete'), {
         method: 'DELETE',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ tag: t })
      }).then(res => res.json()).then(() => {
         const newTags = { ...storedTags };
         newTags[group] = newTags[group].filter(x => x !== t);
         updateStoredTags(newTags);
         refreshData();
         setLoading(false);
      }).catch(err => {
         console.error(err);
         setLoading(false);
      });
   };

   return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center backdrop-blur-sm">
         <div className="bg-white rounded-lg shadow-xl w-3/4 max-w-2xl max-h-[85vh] overflow-y-auto overflow-x-hidden p-6 relative">
             <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:bg-gray-200 rounded-full w-8 h-8 text-xl flex items-center justify-center font-bold">×</button>
             <h2 className="text-2xl font-bold mb-4 text-gray-800">🔖 Tag 统一管理中心</h2>
             <p className="text-sm text-gray-600 mb-6 border-l-4 border-yellow-400 pl-3 bg-yellow-50 p-2 rounded">
                 在此处可以全景式管理您添加的各类 Tag。**更名或删除将会穿透式地修改全体库内的所有已关联图谱数据**，请谨慎操作。
             </p>
             
             {loading && <div className="absolute inset-0 bg-white bg-opacity-70 flex justify-center items-center z-10 font-bold text-blue-600 text-xl tracking-widest">🔄 同步修改Database中...</div>}
             
             <div className="space-y-6">
                {Object.entries(storedTags).map(([group, tags]) => (
                   <div key={group} className="border border-gray-200 rounded p-4 bg-gray-50">
                       <h3 className="font-bold text-gray-700 capitalize mb-3 border-b border-gray-300 pb-1">{group} (类别)</h3>
                       <div className="flex flex-wrap gap-2">
                           {tags.map(t => (
                              <div key={t} className="flex items-center bg-white border border-gray-300 rounded shadow-sm group hover:border-blue-400 transition-colors overflow-hidden">
                                  {editingTag?.old === t && editingTag?.group === group ? (
                                      <div className="flex items-center w-full">
                                          <input type="text" className="px-2 py-1 flex-1 text-sm outline-none font-bold text-blue-800 bg-blue-50" value={editValue} onChange={e=>setEditValue(e.target.value)} autoFocus />
                                          <button onClick={saveEdit} className="bg-emerald-500 hover:bg-emerald-600 text-white px-2 py-1 text-sm font-bold">✓</button>
                                          <button onClick={()=>setEditingTag(null)} className="bg-gray-300 hover:bg-gray-400 text-gray-800 px-2 py-1 text-sm font-bold">✕</button>
                                      </div>
                                  ) : (
                                      <>
                                          <span className="px-3 py-1.5 text-sm font-medium text-gray-700 truncate w-32" title={t}>{t}</span>
                                          <button onClick={()=>openEdit(t, group)} className="text-blue-500 hover:bg-blue-100 hover:text-blue-700 px-2 py-1.5 border-l border-gray-200 transition-colors" title="重命名全库 Tag">
                                            ✏️
                                          </button>
                                          <button onClick={()=>deleteTag(t, group)} className="text-red-500 hover:bg-red-100 hover:text-red-700 px-2 py-1.5 border-l border-gray-200 transition-colors" title="抹除此 Tag">
                                            🗑️
                                          </button>
                                      </>
                                  )}
                              </div>
                           ))}
                           {tags.length === 0 && <span className="text-sm text-gray-400 italic">None</span>}
                       </div>
                   </div>
                ))}
             </div>
         </div>
      </div>
   );
}
