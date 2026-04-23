import re
import sys
import os

file_path = "retail_ops/data/products.json"
keys = ["msrp", "current_price", "cost_price"]

def format_match(match):
    prefix = match.group(1)
    value_str = match.group(2)
    try:
        val = float(value_str)
        formatted = f"{val:.2f}"
        return f"{prefix}{formatted}"
    except ValueError:
        return match.group(0)

try:
    print(f"Reading {file_path}...")
    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content
    for key in keys:
        # Regex explanation:
        # ("key":\s*) -> Group 1: key and whitespace
        # (\d+(\.\d*)?) -> Group 2: the number (int or float)
        pattern = re.compile(f'("{key}":\\s*)(\\d+(\\.\\d*)?)')
        content = pattern.sub(format_match, content)

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Successfully updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
