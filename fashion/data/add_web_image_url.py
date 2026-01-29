import json
import os

def add_web_image_url():
    file_path = "fashion/data/products.json"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        products = json.load(f)

    updated_count = 0
    for p in products:
        if "media" in p and "main_image_url" in p["media"]:
            main_url = p["media"]["main_image_url"]
            if main_url:
                # Split extension
                parts = os.path.splitext(main_url)
                web_url = f"{parts[0]}_min{parts[1]}"
                
                # Insert web_image_url after main_image_url if possible, or just add it
                # Dictionary order is preserved in recent Python, but to be sure we can rebuild the dict
                new_media = {}
                for k, v in p["media"].items():
                    new_media[k] = v
                    if k == "main_image_url":
                        new_media["web_image_url"] = web_url
                
                p["media"] = new_media
                updated_count += 1

    with open(file_path, "w") as f:
        json.dump(products, f, indent=2)
    
    print(f"Updated {updated_count} products in {file_path}")

if __name__ == "__main__":
    add_web_image_url()
