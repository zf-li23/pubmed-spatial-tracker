import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/frontend/src/components/AnnotationForm.jsx", "r") as f:
    text = f.read()

# fix onSaveUrlOnly overwriting pdf_path
old_str_saved = 'onUpdateContent({ ...row, category: cat, tags: joinedTags, is_manually_confirmed: true, pdf_path: data.path, url: pdfUrl });'
new_str_saved = 'onUpdateContent({ ...row, category: cat, tags: joinedTags, is_manually_confirmed: true, url: data.path });'
text = text.replace(old_str_saved, new_str_saved)

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/frontend/src/components/AnnotationForm.jsx", "w") as f:
    f.write(text)
print("AnnotationForm fixed 2")
