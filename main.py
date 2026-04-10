# -*- coding: utf-8 -*-
"""
PubMed 空间转录组学文献采集与追踪工具
用于批量检索空间转录组学相关文献，并对文献进行分类和标注，最终生成结构化数据表格供下游分析。
"""

import os
import re
import pandas as pd
from Bio import Entrez
import urllib.error
import time
from tqdm import tqdm
import json
import migrate_naive

# ---------------------------------------------------------
# 动态加载 tags.json 与 构建检索式
# ---------------------------------------------------------
TAG_GROUPS = migrate_naive.TAG_GROUPS

# 从 tags.json 的 technology 列表中抽取技术关键词，并动态拼装到 PubMed 检索式中
tech_tags = TAG_GROUPS.get("technology", [])
tech_queries = [f"{t}[Title/Abstract]" if t.lower() not in ["visium"] else f"({t}[Title/Abstract] AND transcriptom*[Title/Abstract])" for t in tech_tags]

# 核心空间转录组学通用词
base_queries = [
    '"spatial transcriptomics"[Title/Abstract]',
    '"spatially resolved transcriptomics"[Title/Abstract]',
    '"spatial gene expression"[Title/Abstract]',
    '"spatial omics"[Title/Abstract]'
]

# 完全动态拼接
QUERY = " OR ".join(base_queries + tech_queries)

# ---------------------------------------------------------
# 配置参数
# ---------------------------------------------------------
# 请务必修改为您自己的邮箱地址，否则可能会被 NCBI 拒绝访问
EMAIL = "zf-li23@mails.tsinghua.edu.cn"  
MAX_RESULTS = 10000  # 为了测试，默认获取 100 篇。如需获取全部，可以自行增大该数值（例如 10000）

# 输出文件名配置
DB_OUTPUT_FILE = "spatial_literature.db"
import sqlite3
from sqlalchemy import create_engine
engine = create_engine(f"sqlite:///{DB_OUTPUT_FILE}")
TEMPLATE_FILE = "template.xlsx"

# ---------------------------------------------------------
# 外部常数 (用于预印本判定等)
# ---------------------------------------------------------
PREPRINT_JOURNALS = ["biorxiv", "medrxiv", "arxiv"]

def create_template(filename: str):
    """
    生成一个空的 Excel 模板文件（仅包含列头），供用户参考。
    """
    columns = [
        "pmid", "doi", "title", "journal", "pub_year", "category", "tags",
        "is_manually_confirmed", "annotation_batch", "pdf_path", "url", 
        "abstract", "mesh_terms", "keywords", "is_preprint", "is_method_note", 
        "citation_count", "notes", "auto_predicted_category", "auto_predicted_tags",
        "naive_category", "naive_tags"
    ]
    df = pd.DataFrame(columns=columns)
    df.to_excel(filename, index=False)
    print(f"[*] 已生成空模板文件: {filename}")

def fetch_pubmed(email: str, query: str, max_results: int = 100) -> list:
    """
    从 PubMed 检索文献并获取 XML 元数据
    """
    Entrez.email = email
    print(f"[*] 正在检索 PubMed，最大获取条数: {max_results}...")
    try:
        # 1. 检索 PMIDs
        search_handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        search_results = Entrez.read(search_handle)
        search_handle.close()
        
        id_list = search_results.get("IdList", [])
        if not id_list:
            print("[-] 未找到相关文献。")
            return []
            
        print(f"[*] 发现 {len(id_list)} 篇待下载...")
        # (已移除废弃文本过滤的机制，现在所有数据仍将入库，靠标签作分类器分类基础)

        # 2. 分批次获取 XML 原数据并展示进度条
        batch_size = 200
        articles = []
        print(f"[*] 检索到 {len(id_list)} 篇文献，正在分批下载元数据...")
        for start in tqdm(range(0, len(id_list), batch_size), desc="下载进度", unit="批次"):
            end = min(len(id_list), start + batch_size)
            batch_ids = id_list[start:end]
            try:
                fetch_handle = Entrez.efetch(db="pubmed", id=",".join(batch_ids), retmode="xml")
                batch_results = Entrez.read(fetch_handle)
                fetch_handle.close()
                articles.extend(batch_results.get("PubmedArticle", []))
            except Exception as batch_e:
                print(f"\n[-] 第 {start}-{end} 批次下载失败: {batch_e}，跳过此批次。")
                time.sleep(2)
        
        return articles
        
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP 错误: {e}")
        return []
    except Exception as e:
        print(f"[-] 检索失败: {e}")
        return []

def parse_article(record: dict) -> dict:
    """
    解析单篇 PubMed XML 记录，提取所需关键信息
    """
    medline = record.get("MedlineCitation", {})
    article = medline.get("Article", {})
    
    # 提取 PMID
    pmid = str(medline.get("PMID", ""))
    
    # 提取 DOI
    doi = ""
    article_id_list = record.get("PubmedData", {}).get("ArticleIdList", [])
    for aid in article_id_list:
        if aid.attributes.get("IdType") == "doi":
            doi = str(aid)
            break
            
    # 提取标题
    title = article.get("ArticleTitle", "")
    
    # 提取期刊
    journal = article.get("Journal", {}).get("Title", "")
    
    # 提取年份
    pub_year = ""
    pub_date = article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
    if "Year" in pub_date:
        pub_year = pub_date["Year"]
    elif "MedlineDate" in pub_date: # 有些文章日期是 "2023 Jan-Feb"
        match = re.search(r"\d{4}", pub_date["MedlineDate"])
        if match:
            pub_year = match.group(0)
            
    # 提取摘要文本
    abstract_texts = article.get("Abstract", {}).get("AbstractText", [])
    abstract = " ".join([str(t) for t in abstract_texts]) if abstract_texts else ""
    
    # 提取 MeSH 词 (Medical Subject Headings)
    mesh_terms = []
    mesh_list = medline.get("MeshHeadingList", [])
    for mesh in mesh_list:
        descriptor = mesh.get("DescriptorName", "")
        if descriptor:
            mesh_terms.append(str(descriptor))
    mesh_str = "; ".join(mesh_terms)
    
    # 提取关键词 (Keywords)
    keywords = []
    keyword_list_wrapper = medline.get("KeywordList", [])
    if keyword_list_wrapper:
        for kw in keyword_list_wrapper[0]:
            keywords.append(str(kw))
    keywords_str = "; ".join(keywords)
    
    return {
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "pub_year": pub_year,
        "journal": journal,
        "abstract": abstract,
        "mesh_terms": mesh_str,
        "keywords": keywords_str
    }

def classify_article(parsed_data: dict) -> tuple:
    """
    基于简单的关键字规则对文献进行预分类和打标签。
    通过调用 migrate_naive 中的 get_naive 方法，统一采用 tags.json 管理。
    """
    import migrate_naive
    
    title_lower = str(parsed_data.get("title", "")).lower()
    journal_lower = str(parsed_data.get("journal", "")).lower()
    
    # ==== 1. 预印本判定 ====
    is_preprint = any(pj in journal_lower for pj in PREPRINT_JOURNALS)
    
    # ==== 2. 方法注释/评论判定 ====
    is_method_note = any(kw in title_lower for kw in ["method note", "protocol", "comment", "erratum", "correction"])
    
    # ==== 3. 依赖 rules 获取 category 和 tags ====
    category, tags_str = migrate_naive.get_naive(
        parsed_data.get("title", ""),
        parsed_data.get("abstract", ""),
        parsed_data.get("journal", "")
    )
    
    parsed_data["category"] = category
    parsed_data["tags"] = tags_str
    parsed_data["is_preprint"] = is_preprint
    parsed_data["is_method_note"] = is_method_note
    parsed_data["notes"] = ""
    parsed_data["citation_count"] = "N/A" # 暂不通过PubMed直接抓取被引量，推荐第三方API

    # 按照 PubMed 和要求的先后顺序编排字段并返回
    return {
        "pmid": parsed_data.get("pmid", ""),
        "doi": parsed_data.get("doi", ""),
        "title": parsed_data.get("title", ""),
        "abstract": parsed_data.get("abstract", ""),
        "pub_year": parsed_data.get("pub_year", ""),
        "journal": parsed_data.get("journal", ""),
        "category": parsed_data.get("category", ""),
        "tags": parsed_data.get("tags", ""),
        "mesh_terms": parsed_data.get("mesh_terms", ""),
        "keywords": parsed_data.get("keywords", ""),
        "is_preprint": parsed_data.get("is_preprint", False),
        "is_method_note": parsed_data.get("is_method_note", False),
        "citation_count": parsed_data.get("citation_count", "N/A"),
        "is_manually_confirmed": False, # 默认未经人工校验
        "pdf_path": "", # 倒数第二列：本地PDF存储路径
        "notes": parsed_data.get("notes", "") # 备注放在最后一列
    }

def save_to_file(data: list, excel_filename: str):
    """
    将处理好的一组字典列表转化为 DataFrame 并保存为 Excel。
    在保存之前，如果已经存在同名文件，会进行增量合并：
    - 保留所有 `is_manually_confirmed` 为 True 的现有行，防止人工标注数据被覆盖
    - 更新未确认或新增的行
    """
    if not data:
        print("[-] 没有数据可供保存。")
        return
        
    new_df = pd.DataFrame(data)
    
    if os.path.exists(excel_filename):
        try:
            old_df = pd.read_excel(excel_filename)
            print(f"[*] 发现已有数据表，包含 {len(old_df)} 条记录，正在执行智能合并...")
            
            # 把 pmid 强制转字符串进行严谨匹配
            old_df["pmid"] = old_df["pmid"].astype(str)
            new_df["pmid"] = new_df["pmid"].astype(str)
            
            # 提取其中已经是"手动确认"过的保留名单数据 (is_manually_confirmed == True/1)
            confirmed_mask = old_df["is_manually_confirmed"] == True
            confirmed_df = old_df[confirmed_mask]
            
            # 获取已经确定的 pmid 集合
            confirmed_pmids = set(confirmed_df["pmid"].tolist())
            print(f"[*] 侦测到 {len(confirmed_pmids)} 篇已被人工审核锁定的文献，这部分将完全免疫爬虫覆盖！")
            
            # 从本次新爬取的数据中，剔除掉那些在此前已经被人工确认的项 (不作更新)
            new_unconfirmed_df = new_df[~new_df["pmid"].isin(confirmed_pmids)]
            
            # 在旧的数据表中，把那些还没被确认过的数据剔除掉，给新数据腾位置（覆盖未确认的项）
            old_unconfirmed_df = old_df[~confirmed_mask]
            # 那些既不在新爬取结果中，也没有确定的旧数据，看各位意愿，一般保留 (防止某次爬虫关键词窄没爬到)
            # 所以未确认的数据：合并策略是新爬到的覆盖旧的。
            old_unconfirmed_keep_df = old_unconfirmed_df[~old_unconfirmed_df["pmid"].isin(set(new_df["pmid"].tolist()))]
            
            # 增量处理 annotation_batch: 分配给新流入文章或者补齐以前缺失的 (默认用最末尾的 batch 或 1000 以示为新增的大块)
            final_df = pd.concat([confirmed_df, old_unconfirmed_keep_df, new_unconfirmed_df], ignore_index=True)
            
            if "annotation_batch" not in final_df.columns:
                 final_df["annotation_batch"] = 0
            if "auto_predicted_category" not in final_df.columns:
                 final_df["auto_predicted_category"] = final_df["category"]
                 
            # 如果有新文章没有任何批次，将它们放到最后一个 batch 或者新建一个 batch
            max_batch = final_df["annotation_batch"].max()
            if pd.isna(max_batch):
                 max_batch = 1
            idx_null_batch = final_df["annotation_batch"].isnull() | (final_df["annotation_batch"] == 0)
            if idx_null_batch.any():
                 final_df.loc[idx_null_batch, "annotation_batch"] = max_batch + 1
                 final_df.loc[idx_null_batch, "auto_predicted_category"] = final_df.loc[idx_null_batch, "category"]
            
            # 让表格重新按照年份和手动状态等排序一下 (可选，主要保持一致)
            final_df.to_excel(excel_filename, index=False)
            print(f"[*] 成功保存增量合并结果至 Excel 文件: {excel_filename}，当前总记录: {len(final_df)}")
        except Exception as e:
            print(f"[-] 增量合并失败: {e}，将尝试直接覆盖备份...")
            new_df.to_excel("backup_new_" + excel_filename, index=False)
    else:
        try:
            new_df.to_excel(excel_filename, index=False)
            print(f"[*] 成功首次保存结果至 Excel 文件: {excel_filename}")
        except Exception as e:
            print(f"[-] 保存 Excel 失败 (请检查是否安装了 openpyxl): {e}")

def main():
    print("="*60)
    print(" 🚀 PubMed 空间转录组文献检索预分类工具启动")
    print("="*60)
    
    # 0. 生成模板文件供参考
    create_template(TEMPLATE_FILE)
    
    if EMAIL == "your.email@example.com":
        print("\n[警告] 您的 EMAIL 尚未配置，这可能会导致请求被 PubMed 屏蔽。建议在代码头部修改。")
        time.sleep(2)
        
    # 1. 抓取文章
    raw_articles = fetch_pubmed(email=EMAIL, query=QUERY, max_results=MAX_RESULTS)
    
    # 1.5 抓取手动导入的文献（为了复现环境）
    manual_pmids_path = "manual_imported_pmids.txt"
    if os.path.exists(manual_pmids_path):
        try:
            with open(manual_pmids_path, "r", encoding="utf-8") as fpmids:
                manual_ids = [line.strip() for line in fpmids if line.strip().isdigit()]
            if manual_ids:
                print(f"[*] 发现 {len(manual_ids)} 个手动记录的 PMID，正在补充下载...")
                # 避免重复
                existing_ids = {str(art.get("MedlineCitation", {}).get("PMID", "")) for art in raw_articles}
                needed_ids = [pid for pid in manual_ids if pid not in existing_ids]
                
                if needed_ids:
                    from Bio import Entrez
                    Entrez.email = EMAIL
                    batch_size = 200
                    for start in range(0, len(needed_ids), batch_size):
                        end = min(len(needed_ids), start + batch_size)
                        batch = needed_ids[start:end]
                        try:
                            fetch_handle = Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml")
                            batch_results = Entrez.read(fetch_handle)
                            fetch_handle.close()
                            raw_articles.extend(batch_results.get("PubmedArticle", []))
                        except Exception as e:
                            print(f"[-] 手动批量下载第 {start}-{end} 时失败: {e}")
        except Exception as e:
            print(f"读取手动PMID列表失败: {e}")

    processed_data = []
    print(f"[*] 开始解析并自动分类，共 {len(raw_articles)} 篇...")
    
    # 2. 逐一提取和分类，这里增加一个内部分析进度辅助
    for rec in tqdm(raw_articles, desc="分类进度", unit="篇"):
        try:
            # 第一阶段: 从 XML 提取有效字段 (包括摘要)
            parsed = parse_article(rec)
            if not parsed.get("pmid"):
                continue
                
            # 第二阶段: 基于规则进行预分类分析，存入 naive columns
            naive_cat, naive_tag = classify_article(parsed)
            # Make sure we don't mess up old structure but map to new
            final_record = parsed
            final_record["naive_category"] = naive_cat
            final_record["naive_tags"] = naive_tag
            final_record["category"] = ""
            final_record["tags"] = ""
            final_record["is_manually_confirmed"] = False
            
            processed_data.append(final_record)
        except Exception as e:
            pmid_attempt = rec.get("MedlineCitation", {}).get("PMID", "Unknown")
            print(f"[-] 解析文献 PMID:{pmid_attempt} 时出错: {e}")
            
    # 3. 存储结果文件
    save_to_file(processed_data, EXCEL_OUTPUT_FILE)
    print("="*60)
    print(" 🎉 检索及分类任务完成！")
    print("="*60)

if __name__ == "__main__":
    main()
