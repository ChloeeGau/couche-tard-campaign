import json
import re

# Brand definitions with keywords for simple scoring
BRANDS = {
    "Couche-Tard (Quebec)": {
        "keywords": ["quebec", "winking owl", "mantra", "local", "bilingual", "frais", "rapide", "récompenses", "voisinage", "déjeuner"],
        "negative": ["global", "english-only", "take it easy"]
    },
    "Circle K (Global/Rest of Canada)": {
        "keywords": ["global", "take it easy", "fresh food fast", "polar pop", "fuel", "grab & go", "road trip", "easy", "refresh"],
        "negative": ["quebec", "local-only"]
    }
}

def analyze_product(product):
    text = (
        (product.get("core_identifiers", {}).get("product_name", "") or "") + " " +
        (product.get("description", {}).get("long", "") or "") + " " +
        (product.get("description", {}).get("short", "") or "") + " " +
        (product.get("attributes", {}).get("material", "") or "") + " " +
        (product.get("attributes", {}).get("color_name", "") or "")
    ).lower()
    
    scores = {b: 0 for b in BRANDS}
    
    for brand, criteria in BRANDS.items():
        for kw in criteria["keywords"]:
            if kw in text:
                scores[brand] += 1
        for neg in criteria["negative"]:
            if neg in text:
                scores[brand] -= 2
                
    # Specific overrides or tie-breakers can go here
    
    best_brand = max(scores, key=scores.get)
    return best_brand

def main():
    with open("retail_ops/data/products.json", "r") as f:
        products = json.load(f)
        
    updated_count = 0
    for p in products:
        current_brand = p["core_identifiers"]["brand"]
        new_brand = analyze_product(p)
        
        # Keep existing brand if no clear winner? Or always overwrite? 
        # Request says "Use the description... to find the most suitable brand"
        # So we should probably overwrite.
        
        # Print changes for verification
        # print(f"'{p['core_identifiers']['product_name']}' ({current_brand}) -> {new_brand}")
        
        p["core_identifiers"]["brand"] = new_brand
        updated_count += 1
        
    with open("retail_ops/data/products.json", "w") as f:
        json.dump(products, f, indent=2)
    
    print(f"Updated {updated_count} products.")

if __name__ == "__main__":
    main()
