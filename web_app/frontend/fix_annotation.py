import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/frontend/src/components/AnnotationForm.jsx", "r") as f:
    text = f.read()

# in handleFileUpload
text = text.replace('pdf_path: res.path });', 'pdf_path: res.path, url: row.url });')

# in onUrlSubmit (downloads PDF)
text = text.replace('pdf_path: data.path });', 'pdf_path: data.path, url: pdfUrl });')

# in onSaveUrlOnly
text = text.replace('is_manually_confirmed: true, pdf_path: data.path });', 'is_manually_confirmed: true, url: data.path });')

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/frontend/src/components/AnnotationForm.jsx", "w") as f:
    f.write(text)
print("AnnotationForm fixed")
