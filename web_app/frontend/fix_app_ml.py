import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py", "r") as f:
    text = f.read()

old_ml_logic = """    X_train = (confirmed_df["title"].fillna("") + " " + confirmed_df["abstract"].fillna("")).tolist()
    Y_train = confirmed_df["category"].tolist()
    
    text_clf = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)),
        ('clf', MultinomialNB()),
    ])
    
    text_clf.fit(X_train, Y_train)
    
    target_idx = df[(df["annotation_batch"] == next_batch) & (df["is_manually_confirmed"] == False)].index
    predicted_count = 0
    if not target_idx.empty:
        X_target = (df.loc[target_idx, "title"].fillna("") + " " + df.loc[target_idx, "abstract"].fillna("")).tolist()
        predicted_cats = text_clf.predict(X_target)
        
        df.loc[target_idx, "category"] = predicted_cats
        df.loc[target_idx, "auto_predicted_category"] = predicted_cats
        predicted_count = len(target_idx)
        
    save_df(df)"""

new_ml_logic = """    X_train = (confirmed_df["title"].fillna("") + " " + confirmed_df["abstract"].fillna("")).tolist()
    Y_train_category = confirmed_df["category"].tolist()
    # Use fillna for tags string, so we predict exact tag combination
    Y_train_tags = confirmed_df["tags"].fillna("").tolist()
    
    # Train Category Model
    text_clf_cat = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)),
        ('clf', MultinomialNB()),
    ])
    text_clf_cat.fit(X_train, Y_train_category)
    
    # Train Tags Model
    text_clf_tags = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)),
        ('clf', MultinomialNB()),
    ])
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
        
    save_df(df)"""

text = text.replace(old_ml_logic, new_ml_logic)

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py", "w") as f:
    f.write(text)
print("app.py ML prediction tags updated")
