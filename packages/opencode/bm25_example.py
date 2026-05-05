from rank_bm25 import BM25Okapi
import re

def preprocess(text):
    return re.findall(r'\w+', text.lower())

corpus = [
    "The quick brown fox jumps over the lazy dog",
    "A quick brown fox never sleeps",
    "The lazy dog is sleeping",
    "Quick foxes are clever"
]

tokenized_corpus = [preprocess(doc) for doc in corpus]

bm25 = BM25Okapi(tokenized_corpus)

query = "quick fox"
tokenized_query = preprocess(query)

scores = bm25.get_scores(tokenized_query)

for i, score in enumerate(scores):
    print(f"Doc {i}: {corpus[i]} => Score: {score:.4f}")

top_results = bm25.get_top_n(tokenized_query, corpus, n=2)
print("\nTop 2 results:")
for doc in top_results:
    print(f"  - {doc}")
