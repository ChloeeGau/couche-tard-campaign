import json
import os

def add_brand_guide_url():
    file_path = "fashion/data/brands.json"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        brands = json.load(f)

    updated_count = 0
    for b in brands:
        if "brand_identifier" in b:
            bid = b["brand_identifier"]
            url = f"https://storage.cloud.google.com/creative-content/brands/{bid}/style_guide_{bid}.docx"
            
            # Insert brand_guide_url generally after name or brand_identifier
            # We recreate the dict to control order somewhat, though mostly for readability
            new_b = {}
            for k, v in b.items():
                new_b[k] = v
                if k == "name":
                    new_b["brand_guide_url"] = url
            
            # If name wasn't there (unlikely), just add it
            if "brand_guide_url" not in new_b:
                new_b["brand_guide_url"] = url
                
            # Update the object in list
            # We can't just assign new_b to b directly in the loop if we want to replace the object reference in the list?
            # Actually we can iterating by index or just modifying b if we don't care about order.
            # But I created new_b to preserve order.
            # Let's replace the item in the list.
            pass
        
    # Re-loop to replace properly
    new_brands = []
    for b in brands:
        if "brand_identifier" in b:
            bid = b["brand_identifier"]
            url = f"https://storage.cloud.google.com/creative-content/brands/{bid}/style_guide_{bid}.docx"
            new_b = {}
            # order: identifier, name, brand_guide_url, then rest
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
