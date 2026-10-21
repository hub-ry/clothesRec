import json
import numpy as np
from sklearn.cluster import KMeans

arr = np.load("data/embeddings.npy") # the 2d 'array'

# corresponding items that made it through
with open("data/kept.json") as f:
    kept = json.load(f)

print(arr.shape, len(kept))

#normalize for simplicy for when calc cosine similarity

arr = arr / np.linalg.norm(arr, axis=1, keepdims=True)

km = KMeans(n_clusters=8, random_state=0).fit(arr)

print(np.bincount(km.labels_))


