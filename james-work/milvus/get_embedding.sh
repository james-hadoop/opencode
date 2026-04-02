#!/bin/bash
# 使用系统 Python 加载模型并输出向量

/usr/bin/python3 -c "
from sentence_transformers import SentenceTransformer
import json
import sys

model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
query = sys.argv[1]
vector = model.encode(query).tolist()
print(json.dumps(vector))
" "$1"
