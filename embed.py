import json, io
import requests
import torch
import numpy as np
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32") # model to interpret images
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32") # fits any image into the input format for model

with open("data/products.json") as f:
    items = json.load(f)



vecs = []
kept = []

for item in items [:10]:
    try:
        resp = requests.get(item["image"]) # download the photo bytes
        img = Image.open(io.BytesIO(resp.content)).convert("RGB") # open as image
        inputs = processor(images=img, return_tensors="pt") # processor resize to CLIP format
        with torch.no_grad():
            vec = model.get_image_features(**inputs) # model return 512 numbers
    except Exception as e:
        print("skip", item["title"], e)
        continue
    vecs.append(vec[0])
    kept.append(item)


arr = np.stack([v.numpy() for v in vecs]) 
# turns all the 512 dim vecotrs in to a 2d array, so you can compare
# with others without a loop , matrix multiply
np.save("data/embeddings.npy", arr)
arr = np.load("data/embeddings.npy")

with open("data/kept.json", "w") as f:
    json.dump(kept, f, indent=2)


print(len(vecs), len(kept))
