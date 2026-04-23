from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import json
import random
import uuid
from datetime import datetime, date, timedelta
import calendar
import os


# 1. CONFIGURATION
# ---------------------------------------------------------
# TODO: Replace with your actual Project ID
PROJECT_ID = "analytics-demo-cg"
DATASET_ID = "Couche_Tard_Marketing"
JSON_FILE_PATH = "/Users/chloegaudreau/.gemini/jetski/scratch/wef-2026-fashion-campaign/bq_product.json"  # Ensure this file exists in the directory

# Initialize Client
client = bigquery.Client(project=PROJECT_ID)

# 2. LOAD PRODUCT DATA
# ---------------------------------------------------------
print(f"Loading data from {JSON_FILE_PATH}...")
if not os.path.exists(JSON_FILE_PATH):
    raise FileNotFoundError(f"Error: '{JSON_FILE_PATH}' not found.")

with open(JSON_FILE_PATH, 'r') as file:
    products_data = json.load(file)
    print(f"Loaded {len(products_data)} products.")

# 3. SETUP DATASET & SCHEMAS
# ---------------------------------------------------------
dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
try:
    client.get_dataset(dataset_ref)
    print(f"Dataset {DATASET_ID} exists.")
except NotFound:
    client.create_dataset(bigquery.Dataset(dataset_ref))
    print(f"Created dataset {DATASET_ID}.")

# Schemas
plan_schema = [
    bigquery.SchemaField("plan_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("sku", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("plan_month", "DATE", mode="REQUIRED"), 
    bigquery.SchemaField("estimated_units", "INT64"),
    bigquery.SchemaField("seasonality_factor", "FLOAT64"), 
]

inventory_schema = [
    bigquery.SchemaField("sku", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("product_name", "STRING"),
    bigquery.SchemaField("category", "STRING"),
    bigquery.SchemaField("sub_category", "STRING"),
    bigquery.SchemaField("price", "FLOAT64"),
    bigquery.SchemaField("stock_quantity", "INT64"),
]

sales_schema = [
    bigquery.SchemaField("sale_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("sku", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("quantity_sold", "INT64"),
    bigquery.SchemaField("total_amount", "FLOAT64"),
    bigquery.SchemaField("sale_date", "DATE"),
]

def get_table_id(name, schema):
    t_id = f"{PROJECT_ID}.{DATASET_ID}.{name}"
    try:
        client.get_table(t_id)
        # Delete and recreate to ensure a clean slate for this run
        client.delete_table(t_id)
        client.create_table(bigquery.Table(t_id, schema=schema))
    except NotFound:
        print(f"Table {t_id} not found. Creating...")
        client.create_table(bigquery.Table(t_id, schema=schema))
    return t_id

plan_table_id = get_table_id("sales_plan", plan_schema)
inv_table_id = get_table_id("inventory", inventory_schema)
sales_table_id = get_table_id("sales", sales_schema)

# 4. LOGIC: SEASONALITY HELPER
# ---------------------------------------------------------
def get_seasonality_multiplier(product, month):
    text = (product['core_identifiers']['product_name'] + " " + 
            product['categorization'].get('sub_category', '')).lower()
    
    is_winter = month in [11, 12, 1, 2]
    is_summer = month in [5, 6, 7, 8]
    
    if any(x in text for x in ['sloche', 'cold beverage', 'frozen', 'fountain', 'water']):
        return 2.2 if is_summer else 0.8
    if any(x in text for x in ['coffee', 'pizza', 'hot food', 'breakfast', 'roller grill']):
        return 1.6 if is_winter else 0.8
    if any(x in text for x in ['fuel', 'gasoline', 'diesel']):
        return 1.2 if is_summer else 1.0
        
    return 1.0 

# 5. STEP 1: GENERATE & LOAD SALES PLAN (2025-2026)
# ---------------------------------------------------------
print("\n--- Step 1: Generating Sales Plan (2025-2026) ---")

plan_rows_buffer = []
local_plan_cache = [] 

years = [2025, 2026]
months = range(1, 13)

for product in products_data:
    sku = product['core_identifiers']['sku']
    base_monthly_sales = random.randint(20, 50)
    
    for year in years:
        for month in months:
            factor = get_seasonality_multiplier(product, month)
            estimated_units = int(base_monthly_sales * factor)
            estimated_units = max(1, estimated_units)
            
            plan_date = date(year, month, 1)
            
            row = {
                "plan_id": str(uuid.uuid4()),
                "sku": sku,
                "plan_month": plan_date.strftime("%Y-%m-%d"),
                "estimated_units": estimated_units,
                "seasonality_factor": factor
            }
            plan_rows_buffer.append(row)
            
            local_plan_cache.append({
                "sku": sku,
                "year": year,
                "month": month,
                "target_units": estimated_units,
                "price": product['commercial_status']['current_price']
            })

# Batch Insert Plan
chunk_size = 1000
for i in range(0, len(plan_rows_buffer), chunk_size):
    errors = client.insert_rows_json(plan_table_id, plan_rows_buffer[i:i+chunk_size])
    if errors: print(f"Errors inserting plan chunk {i}: {errors}")

print(f"Successfully loaded {len(plan_rows_buffer)} rows into 'sales_plan'.")

# 6. STEP 2: LOAD INVENTORY
# ---------------------------------------------------------
print("\n--- Step 2: Loading Inventory ---")

inv_rows = []
for p in products_data:
    inv_rows.append({
        "sku": p['core_identifiers']['sku'],
        "product_name": p['core_identifiers']['product_name'],
        "category": p['categorization']['category'],
        "sub_category": p['categorization'].get('sub_category'),
        "price": p['commercial_status']['current_price'],
        "stock_quantity": p['commercial_status']['stock_quantity']
    })

errors = client.insert_rows_json(inv_table_id, inv_rows)
if not errors:
    print(f"Successfully loaded {len(inv_rows)} rows into 'inventory'.")
else:
    print("Errors inserting inventory:", errors)

# 7. STEP 3: GENERATE SALES 
# ---------------------------------------------------------
print("\n--- Step 3: Generating Sales Transactions ---")

sales_rows_buffer = []

for plan in local_plan_cache:
    
    # --- MODIFIED LOGIC FOR SKU F-PIZZA-001 ---
    if plan['sku'] == "F-PIZZA-001":
        # Force huge underperformance (15% to 35% of plan)
        variance = random.uniform(0.15, 0.35)
    else:
        # Standard performance (80% to 120% of plan)
        variance = random.uniform(0.8, 1.2)
    # -------------------------------------

    actual_units_to_sell = int(plan['target_units'] * variance)
    
    if actual_units_to_sell <= 0:
        continue
        
    units_sold_so_far = 0
    days_in_month = calendar.monthrange(plan['year'], plan['month'])[1]
    
    while units_sold_so_far < actual_units_to_sell:
        tx_qty = random.randint(1, 3)
        if (units_sold_so_far + tx_qty) > actual_units_to_sell:
            tx_qty = actual_units_to_sell - units_sold_so_far
            
        day = random.randint(1, days_in_month)
        sale_date = date(plan['year'], plan['month'], day).strftime("%Y-%m-%d")
        
        row = {
            "sale_id": str(uuid.uuid4()),
            "sku": plan['sku'],
            "quantity_sold": tx_qty,
            "total_amount": round(tx_qty * plan['price'], 2),
            "sale_date": sale_date
        }
        sales_rows_buffer.append(row)
        units_sold_so_far += tx_qty

# Batch Insert Sales
print(f"Inserting {len(sales_rows_buffer)} sales transactions...")
for i in range(0, len(sales_rows_buffer), chunk_size):
    errors = client.insert_rows_json(sales_table_id, sales_rows_buffer[i:i+chunk_size])
    if errors: print(f"Errors inserting sales chunk {i}: {errors}")

print("Sales table populated.")

# 8. VERIFY RESULTS
# ---------------------------------------------------------
print("\n--- Verification: Jan 2025 Plan vs Sales (Highlighting SKU F-PIZZA-001) ---")

query = f"""
    SELECT 
        p.sku,
        i.product_name,
        p.estimated_units as planned,
        IFNULL(SUM(s.quantity_sold), 0) as actual_sold,
        ROUND((IFNULL(SUM(s.quantity_sold), 0) - p.estimated_units) / p.estimated_units * 100, 1) as variance_pct
    FROM `{PROJECT_ID}.{DATASET_ID}.sales_plan` p
    JOIN `{PROJECT_ID}.{DATASET_ID}.inventory` i ON p.sku = i.sku
    LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.sales` s 
        ON p.sku = s.sku 
        AND DATE_TRUNC(s.sale_date, MONTH) = p.plan_month
    WHERE p.plan_month = '2025-01-01'
    GROUP BY 1, 2, 3
    ORDER BY variance_pct ASC
    LIMIT 5
"""

try:
    job = client.query(query)
    print(f"{'SKU':<10} | {'Product':<30} | {'Plan':<5} | {'Actual':<6} | {'Var %':<6}")
    print("-" * 75)
    for r in job:
        print(f"{r.sku:<10} | {r.product_name[:30]:<30} | {r.planned:<5} | {r.actual_sold:<6} | {r.variance_pct:<6}")
except Exception as e:
    print(f"Query failed: {e}")