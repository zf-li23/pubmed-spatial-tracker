import re
with open("frontend/src/App.jsx", "r") as f:
    text = f.read()

# Replace category colors
text = text.replace(
r"""row.auto_predicted_category ? 'bg-indigo-100 text-indigo-800 border border-indigo-300 border-dashed' :
                                    row.naive_category ? 'bg-gray-100 text-gray-600 border border-gray-300 border-dotted' : 'bg-gray-50 text-gray-400'}`}>""",
"""row.auto_predicted_category ? (row.auto_predicted_category==='Review'?'bg-yellow-200 text-yellow-800' : row.auto_predicted_category==='Technology'?'bg-purple-200 text-purple-800' : row.auto_predicted_category==='Research'?'bg-green-200 text-green-800':'bg-blue-200 text-blue-800') :
                                    row.naive_category ? (row.naive_category==='Review'?'bg-yellow-200 text-yellow-800' : row.naive_category==='Technology'?'bg-purple-200 text-purple-800' : row.naive_category==='Research'?'bg-green-200 text-green-800':'bg-blue-200 text-blue-800') : 'bg-gray-50 text-gray-400'}`}>""")

# Replace tags colors
text = text.replace(
r"""<span className={row.tags?'text-gray-800' : row.auto_predicted_tags?'text-indigo-600' : 'text-gray-500'}>""",
"""<span className="text-gray-800">""")

with open("frontend/src/App.jsx", "w") as f:
    f.write(text)
print("Colors fixed!")
