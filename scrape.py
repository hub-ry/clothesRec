import requests
import time
import json

urls = ["https://haruyama365.com/products.json", "https://velourgarments.eu/products.json", "https://storymfg.com/products.json", "https://3sixteen.com/products.json"
]
items = []
for link in urls:
    page = 1
    while (True):
        resp = requests.get(link, params={"limit":250, "page": page})
        
        if resp.status_code != 200:
            break

        data = resp.json() # split json text to python dict
        products = data["products"]
        if not products:
            break

        # print(len(products))
        #print(products[0]["title"])
        #print(products[0]["images"][0]["src"])
        # print(products[0].keys())
        # title, body_html, product_type, tags, 
        #print(products[0]["body_html"])
        #print(products[0]["variants"][0]["price"])
        

        for p in products:
            
            if not p["images"]:
                continue
            if link == "https://haruyama365.com/products.json" and p["vendor"].lower() != "kapital":
                continue


            item = {
                "title": p["title"],
                "price": p["variants"][0]["price"],
                "body": p["body_html"],
                "type": p["product_type"],
                "tag": p["tags"],
                "brand": link,
                "image":p["images"][0]["src"],
            }

            items.append(item)

        page += 1

with open("data/products.json", "w") as f:
    json.dump(items, f, indent=2)
print(len(items))


