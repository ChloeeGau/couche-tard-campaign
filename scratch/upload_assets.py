from google.cloud import storage
import os

def upload_file(local_path, bucket_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to gs://{bucket_name}/{destination_blob_name}")

bucket = "circlek-demo"
upload_file("retail_ops/data/brand_assets/F-PIZZA-001.png", bucket, "brand_assets/F-PIZZA-001.png")
upload_file("retail_ops/data/brand_assets/BEV-SLO-001.png", bucket, "brand_assets/BEV-SLO-001.png")
