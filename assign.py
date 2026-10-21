import requests
import json,io
from transformers import CLIPModel, CLIPProcessor
import numpy as np
import torch

names = ["workwear", "artisanal", "americana", "earthy", "minimal", "graphic", "knit", "outdoor"]
vibes = [
    "Japanese workwear clothing in indigo denim and sturdy canvas",
    "patchwork boro clothing with visible hand stitching and hand-dyed fabric",
    "rugged American heritage clothing in denim, flannel, and leather",
    "relaxed clothing in muted earth tones like olive, brown, cream, and rust",
    "minimal clothing in black, gray, or white with clean lines and no pattern",
    "clothing with bold graphics, embroidery, or colorful prints",
    "chunky knit sweaters and cardigans with textured wool",
    "outdoor utility clothing like quilted jackets, vests, and technical layers",
]

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32") # model to interpret images
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32") # fits any image into the input format for model


arr = np.load("data/embeddings.npy")
arr = arr / np.linalg.norm(arr, axis=1, keepdims=True)
with open("data/kept.json") as f:
    kept = json.load(f)

inputs = processor(text=vibes, return_tensors="pt", padding=True)


with torch.no_grad():
    out = model.get_text_features(**inputs)

print(type(out))
text=out.pooler_output if hasattr(out, "pooler_output") else out
text_vecs = text.numpy()
text_vecs = text_vecs / np.linalg.norm(text_vecs, axis=1, keepdims=True)

# compare every tiem to every vibe at once with (double for loop)
scores = arr @ text_vecs.T
"""
best = np.argmax(scores, axis=1)

out = []
for i, item in enumerate(kept):
    out.append({**item, "vibe": names[best[i]], "score": float(scores[i][best[i]])})
with open("data/assigned.json", "w") as f:
    json.dump(out, f, indent=2)
"""
types = [item.get("type") or "unknown" for item in kept]

vibe_of = [None] * len(kept)
score_of = [0.0] * len(kept)

for t in set(types):
    idx = [i for i, ty in enumerate(types) if ty == t]   # rows of this type
    group = arr[idx]                                      # (n, 512)

    if len(idx) > 1:
        group = group - group.mean(axis=0)               # strip the "it's a jacket" part
        group = group / np.linalg.norm(group, axis=1, keepdims=True)

    s = group @ text_vecs.T                              # (n, 8)
    b = np.argmax(s, axis=1)
    for k, i in enumerate(idx):                          # map back to global rows
        vibe_of[i] = names[b[k]]
        score_of[i] = float(s[k][b[k]])

out = [{**item, "vibe": vibe_of[i], "score": score_of[i]} for i, item in enumerate(kept)]
with open("data/assigned.json", "w") as f:
    json.dump(out, f, indent=2)
