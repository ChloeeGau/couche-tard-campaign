import json
import re

# Brand definitions with keywords for simple scoring
BRANDS = {
    "Maison Onyx": {
        "keywords": ["satin", "silk", "leather", "velvet", "black", "gold", "evening", "glam", "luxury", "drape", "sequin", "metallic", "pearl", "cocktail", "sheath", "quilted", "chain", "party", "night"],
        "negative": ["casual", "sneaker", "fleece", "jogger", "hiking", "cargo", "flannel"]
    },
    "Modern Muse": {
        "keywords": ["office", "professional", "blazer", "tailored", "structure", "beige", "cream", "navy", "work", "desk", "classic", "essential", "capsule", "minimal", "clean", "pencil skirt", "trouser", "shirtdress", "satin"],
        "negative": ["distressed", "ripped", "neon", "acid", "grunge"]
    },
    "Neon & Co.": {
        "keywords": ["bright", "pink", "blue", "fun", "trendy", "denim", "graphic", "casual", "weekend", "playful", "candy", "bubblegum", "kicks", "sneaker", "miniskirt", "plaid", "tartan", "check", "slogan"],
        "negative": ["evening gown", "silk", "formal", "office", "wool"]
    },
    "Volt": {
        "keywords": ["distressed", "ripped", "cyber", "street", "acid", "green", "orange", "silver", "metal", "edgy", "urban", "grunge", "fleece", "jogger", "sweatpant", "cargo", "tech", "utility"],
        "negative": ["floral", "romantic", "lace", "pearl", "gown"]
    },
    "Aurum": {
        "keywords": ["linen", "organic", "natural", "sustainable", "quiet", "earth", "sand", "sage", "timeless", "flower", "floral", "bloom", "garden", "viscose", "cotton", "ditsy", "maxi", "a-line", "breezy", "soft"],
        "negative": ["neon", "plastic", "polyester", "synthetic", "sequin"]
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
                
    # Specific overrides or tie-breakers
    # If "floral" is prominent, unlikely to be Volt or Maison Onyx usually, more Aurum or Modern Muse (but Aurum has 'flower' keywords)
    # The prompt specifices Aurum is "Sustainable Quiet Luxury" - often linen, organic.
    # Note: "Ditsy floral" likely fits Aurum ("Spring Bloom" in original descriptions might map to Aurum or Modern Muse, but Aurum has 'sage', 'sand', 'nature')
    
    best_brand = max(scores, key=scores.get)
    return best_brand

def main():
    with open("fashion/data/products.json", "r") as f:
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
        
    with open("fashion/data/products.json", "w") as f:
        json.dump(products, f, indent=2)
    
    print(f"Updated {updated_count} products.")

if __name__ == "__main__":
    main()
