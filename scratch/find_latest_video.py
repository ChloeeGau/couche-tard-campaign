from google.cloud import storage
import time

def find_latest_file(bucket_name, prefix, extension):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    
    latest_blob = None
    latest_time = 0
    
    for blob in blobs:
        if blob.name.endswith(extension):
            if blob.updated.timestamp() > latest_time:
                latest_time = blob.updated.timestamp()
                latest_blob = blob
                
    return latest_blob

bucket = "circlek-demo"
latest = find_latest_file(bucket, "", ".mp4")

if latest:
    print(f"Found latest video: gs://{bucket}/{latest.name}")
    # Download it
    target = "tests/latest_campaign_video.mp4"
    latest.download_to_filename(target)
    print(f"Downloaded to {target}")
else:
    print("No video found.")
