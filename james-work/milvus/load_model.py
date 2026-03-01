import os
os.environ['GLOG_minloglevel'] = '3'

from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
print('MODEL_LOADED_SUCCESS')
