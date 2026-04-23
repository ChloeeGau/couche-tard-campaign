import json
import os

def add_brand_guide_url():
    file_path = "retail_ops/data/brands.json"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        brands = json.load(f)

    updated_count = 0
    new_brands = []
    for b in brands:
        if "brand_identifier" in b:
            bid = b["brand_identifier"]
            if "couche_tard" in bid:
                url = "retail_ops/data/brand_assets/couche_tard_style_guide.md"
            else:
                url = "retail_ops/data/brand_assets/circle_k_style_guide.md"
                
            new_b = {}
            new_b["brand_identifier"] = b.get("brand_identifier")
            new_b["name"] = b.get("name")
            new_b["brand_guide_url"] = url
            for k, v in b.items():
                if k not in ["brand_identifier", "name", "brand_guide_url"]:
                    new_b[k] = v
            new_brands.append(new_b)
            updated_count += 1
        else:
            new_brands.append(b)

    with open(file_path, "w") as f:
        json.dump(new_brands, f, indent=2)
    
    print(f"Updated {updated_count} brands in {file_path}")

if __name__ == "__main__":
    add_brand_guide_url()
