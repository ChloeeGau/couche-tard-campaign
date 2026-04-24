from google.cloud import storage

def download_file(bucket_name, source_blob_name, local_path):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(local_path)
    print(f"Downloaded gs://{bucket_name}/{source_blob_name} to {local_path}")

bucket = "circlek-demo"
source = "20260423223912778140_4h5z/scene_video_1_1776998352.mp4"
target = "tests/final_campaign_video_2.mp4"

download_file(bucket, source, target)
