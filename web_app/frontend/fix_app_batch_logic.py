import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py", "r") as f:
    content = f.read()

# Regex to safely replace trigger_active_learning
pattern = r"def trigger_active_learning\(\):[\s\S]*?save_df\(df\)[\s\S]*?return \{[^\}]*\}"

new_func = """def trigger_active_learning():
    df = get_df()
    
    if "annotation_batch" not in df.columns:
        raise HTTPException(status_code=400, detail="Database not upgraded with active learning schema.")
        
    unconfirmed_df = df[df["is_manually_confirmed"] == False]
    if unconfirmed_df.empty:
        return {"message": "✅ 恭喜！当前库中所有文章均已校验完毕！", "status": "done"}
        
    next_batch = int(unconfirmed_df["annotation_batch"].min())
    
    # 核心修改：只选用在此之前的所有完整批次作为训练集，并且排除掉未来批次的零散已校验数据
    # 以免训练池混入杂乱的信息
    confirmed_df = df[(df["is_manually_confirmed"] == True) & (df["annotation_batch"] < next_batch)]
    
    if confirmed_df.empty:
        return {
            "message": "请至少先标注并校验【第 1 批次】的全量数据，模型才拥有无污染的基线样本来学习！", 
            "status": "need_data",
            "next_batch": next_batch
        }

    # Evaluate ONLY on the last completed batch to give a clean performance report
    eval_batch = next_batch - 1
    eval_df = confirmed_df[confirmed_df["annotation_batch"] == eval_batch]
    
    accuracy = 0
    if not eval_df.empty and "auto_predicted_category" in eval_df.columns and not eval_df["auto_predicted_category"].isna().all():
        y_true = eval_df["category"].astype(str)
        y_pred = eval_df["auto_predicted_category"].astype(str)
        correct = (y_true == y_pred).sum()
        total = len(y_true)
        accuracy = correct / total if total > 0 else 0

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline
    except ImportError:
        raise HTTPException(status_code=500, detail="Please install scikit-learn (`pip install scikit-learn`) to enable the ML module.")

    X_train = (confirmed_df["title"].fillna("") + " " + confirmed_df["abstract"].fillna("")).tolist()
    Y_train_category = confirmed_df["category"].tolist()
    Y_train_tags = confirmed_df["tags"].fillna("").tolist()
    
    # Train Models
    text_clf_cat = Pipeline([('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)), ('clf', MultinomialNB())])
    text_clf_cat.fit(X_train, Y_train_category)
    
    text_clf_tags = Pipeline([('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)), ('clf', MultinomialNB())])
    text_clf_tags.fit(X_train, Y_train_tags)
    
    target_idx = df[(df["annotation_batch"] == next_batch) & (df["is_manually_confirmed"] == False)].index
    predicted_count = 0
    if not target_idx.empty:
        X_target = (df.loc[target_idx, "title"].fillna("") + " " + df.loc[target_idx, "abstract"].fillna("")).tolist()
        
        predicted_cats = text_clf_cat.predict(X_target)
        predicted_tags = text_clf_tags.predict(X_target)
        
        df.loc[target_idx, "category"] = predicted_cats
        df.loc[target_idx, "auto_predicted_category"] = predicted_cats
        
        df.loc[target_idx, "tags"] = predicted_tags
        df.loc[target_idx, "auto_predicted_tags"] = predicted_tags
        
        predicted_count = len(target_idx)
        
    save_df(df)

    return {
        "message": f"🧠 学习完成！\\n本次吸收了 {len(X_train)} 条规范的已标注经验。\\n第 {eval_batch} 批次的大类基线准确率评估：{accuracy:.1%}\\n\\n已成功用净化后的模型对【第 {next_batch} 批次】的 {predicted_count} 条接续数据进行了预测推断！",
        "accuracy": accuracy,
        "next_batch": next_batch,
        "predicted_count": predicted_count,
        "status": "success",
        "training_samples": len(X_train)
    }"""

content = re.sub(pattern, new_func, content)
with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py", "w") as f:
    f.write(content)
print("app.py updated with strictly filtered clean batch logic.")
