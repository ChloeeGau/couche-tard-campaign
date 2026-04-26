from google.cloud import storage

def download_file(bucket_name, source_blob_name, local_path):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(local_path)
    print(f"Downloaded gs://{bucket_name}/{source_blob_name} to {local_path}")

bucket = "circlek-demo"
source = "20260424131947918581_23r0/combined_video_1777051214.mp4"
target = "tests/combined_campaign_video.mp4"

download_file(bucket, source, target)
