import re

with open('web_app/ml_pipeline.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace Review rule
text = re.sub(
    r'elif cat == "Review":.*?elif cat == "Technology":',
    r'''elif cat == "Review":
                    allowed = set(TAG_GROUPS["metaCategory"] + TAG_GROUPS["domain"])
                    tags = extract_top_tags(probs, self.mlb.classes_, allowed, max_n=1, prob_thresh=0.0)
                elif cat == "Technology":''',
    text,
    flags=re.DOTALL
)

# Replace Research rule
text = re.sub(
    r'elif cat == "Research":.*?elif cat == "Database":',
    r'''elif cat == "Research":
                    domain_tags = extract_top_tags(probs, self.mlb.classes_, set(TAG_GROUPS["domain"]), max_n=1, prob_thresh=0.0)
                    tech_tags = extract_top_tags(probs, self.mlb.classes_, set(TAG_GROUPS["technology"]), max_n=1, prob_thresh=0.6)
                    tags = domain_tags + tech_tags
                elif cat == "Database":''',
    text,
    flags=re.DOTALL
)

with open('web_app/ml_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(text)

