import sys
import json

from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
model_dim = model.get_sentence_embedding_dimension()

query = sys.argv[1]
vector = model.encode(query).tolist()

print(json.dumps(vector))
