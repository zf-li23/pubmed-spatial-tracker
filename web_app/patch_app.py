import sys

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_logic = """@app.get("/api/articles")
def get_articles():
    df = get_df()
    if df.empty:
        return []
    
    if "uncertainty_score" not in df.columns:
        df["uncertainty_score"] = 0.0
        
    df = df.fillna("")
    
    # 按照 is_manually_confirmed=False 置顶，并在 False 组内部随机性分数为 DESC (高置信度=低分, 越不懂得分越高)
    df['is_confirmed_num'] = df['is_manually_confirmed'].astype(int)
    df['uncertainty_score_num'] = pd.to_numeric(df['uncertainty_score'], errors='coerce').fillna(0.0)
    df = df.sort_values(by=['is_confirmed_num', 'uncertainty_score_num'], ascending=[True, False])
    df = df.drop(columns=['is_confirmed_num', 'uncertainty_score_num'])
    
    return df.to_dict(orient="records")

class AnnotationData(BaseModel):
    category: str
    tags: str

@app.post("/api/ml/active_learning")
def trigger_active_learning():
    df = get_df()
    
    confirmed_df = df[df["is_manually_confirmed"] == True]
    unconfirmed_df = df[df["is_manually_confirmed"] == False]
    
    if unconfirmed_df.empty:
        return {"message": "✅ 恭喜！当前库中所有文章均已校验完毕！", "status": "done"}
    
    if len(confirmed_df) < 5:
        return {
            "message": f"当前仅标注了 {len(confirmed_df)} 篇，请至少先标注并校验 10~20 篇数据，模型才拥有足够的基线样本来学习！", 
            "status": "need_data"
        }

    try:
        from ml_pipeline import AutomatedActiveLearner
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Please install required ML libraries! {str(e)}")

    learner = AutomatedActiveLearner()
    
    # 在全部人工确认的数据上进行拟合（Active Learning 的知识吸取）
    learner.fit(confirmed_df)
    
    # 在全部未确认的数据上推送最新预测与计算疑惑度 (Uncertainty Score)
    pred_cats, pred_tags, uncertainties = learner.predict(unconfirmed_df)
    
    # 更新推断与分数
    df.loc[df["is_manually_confirmed"] == False, "auto_predicted_category"] = pred_cats
    df.loc[df["is_manually_confirmed"] == False, "auto_predicted_tags"] = pred_tags
    df.loc[df["is_manually_confirmed"] == False, "uncertainty_score"] = uncertainties
    
    save_df(df)

    return {
        "message": f"🎉 AI 重训成功！\\n基于已标注的 {len(confirmed_df)} 篇样本重构了认知网络。\\n余下无标签文献已按【不确定性分数】重新计算并置顶排列，\\n请在上方优先标注最具有信息量（最棘手）的一批文章！",
        "status": "success"
    }

"""

# replace lines 178 to 373 (0-indexed 177 to 373)
idx_start = -1
idx_end = -1
for i, line in enumerate(lines):
    if line.startswith('@app.get("/api/articles")'):
        idx_start = i
        break

for i in range(idx_start, len(lines)):
    if line.startswith('@app.post("/api/articles/{pmid}/annotate")'):
        break
    if lines[i].startswith('@app.post("/api/articles/{pmid}/annotate")'):
        idx_end = i
        break

if idx_start != -1 and idx_end != -1:
    new_lines = lines[:idx_start] + [new_logic] + lines[idx_end:]
    with open("app.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Replaced lines {} to {}".format(idx_start, idx_end))
else:
    print("Could not find patterns")
