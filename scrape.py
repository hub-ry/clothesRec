import requests
import json

url = "https://haruyama365.com/products.json"
page = 1
items = []
while (True):
    resp = requests.get(url, params={"limit":250, "page": page})
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
        item = {
            "title": p["title"],
            "price": p["variants"][0]["price"],
            "body": p["body_html"],
            "type": p["product_type"],
            "tag": p["tags"],
            "image":p["images"][0]["src"],
        }

        items.append(item)

    page += 1

with open("data/products.json", "w") as f:
    json.dump(items, f, indent=2)
print(len(items))


