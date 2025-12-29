# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import os
from urllib.parse import unquote, urlparse, urlunparse

from dotenv import load_dotenv
from google.api_core.client_info import ClientInfo
from google.cloud import storage

load_dotenv()

AGENT_VERSION = os.environ.get("AGENT_VERSION")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
USER_AGENT = f"cde/enterprise-banking/{AGENT_VERSION}"

GCS_AUTHENTICATED_DOMAIN_SANS_PROTOCOL = "storage.cloud.google.com"
GCS_PUBLIC_DOMAIN_SANS_PROTOCOL = "storage.googleapis.com"

GCS_AUTHENTICATED_DOMAIN = f"https://{GCS_AUTHENTICATED_DOMAIN_SANS_PROTOCOL}/"
GCS_PUBLIC_DOMAIN = f"https://{GCS_PUBLIC_DOMAIN_SANS_PROTOCOL}/"


def upload_to_gcs(
    bucket_path: str, file_bytes: bytes, destination_blob_name: str
) -> str:
    """Uploads a file to Google Cloud Storage

    Args:
        project_id (str): Google Cloud project ID.
        bucket_path (str): Name of the GCS bucket/path (no tailing `/`).
        file_bytes (bytes): The file bytes to upload.
        destination_blob_name (str): Name of the object in the GCS bucket (can be /folder/file.png).

    Returns:
        str: URI to resource in GCS.
    """

    print("Started Uploadig to GCS")
    storage_client = storage.Client(
        project=GOOGLE_CLOUD_PROJECT, client_info=ClientInfo(user_agent=USER_AGENT)
    )

    bucket = storage_client.bucket(bucket_path)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_file(io.BytesIO(file_bytes))

    print(f"File uploaded to gs://{bucket_path}/{destination_blob_name}")

    return f"gs://{bucket_path}/{destination_blob_name}"


def parse_gcs_url(uri: str) -> tuple[str, str]:
    """
    Parses a GCS URI to extract the bucket name and the file path.

    Args:
        uri: A string representing the GCS URI (e.g., "gs://bucket_name/path/to/file").

    Returns:
        A tuple containing:
        (a) The bucket name (str).
        (b) The full path to the file within the bucket (str).

        Raises Exception if the URL is not from a GCS bucket.
    """

    try:
        parts = urlparse(uri)
        if parts.scheme == "gs":
            bucket_name = parts.netloc
            file_path = parts.path.lstrip("/")
            return bucket_name, file_path
        elif (
            GCS_AUTHENTICATED_DOMAIN_SANS_PROTOCOL in parts.netloc
            or GCS_PUBLIC_DOMAIN_SANS_PROTOCOL in parts.netloc
        ):
            # The path will be /bucket-name/path/to/file
            path_parts = parts.path.lstrip("/").split("/", 1)
            if len(path_parts) >= 1 and path_parts[0]:
                bucket_name = path_parts[0]
                file_path = path_parts[1] if len(path_parts) > 1 else ""
                return bucket_name, file_path
    except Exception as e:
        print(f"ERROR parsing GCS URI: {e}")
        raise e

    print(f"ERROR: URI is not from a GCS bucket. URI: {uri}")
    raise ValueError(f"URI is not from a GCS bucket. URI: {uri}")


def check_gcs_file_exists(bucket_name: str, file_path: str) -> bool:
    """Checks if a file exists in a GCS bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.exists()
    except Exception as e:
        print(f"ERROR checking GCS file: {e}")
        return False


def download_from_gcs(uri: str) -> bytes:
    """Downloads a file from Google Cloud Storage and returns its content as bytes.

    Args:
        uri (str): The GCS URI of the object (e.g., "gs://bucket_name/path/to/file").

    Returns:
        bytes: The raw content of the file.
    """
    gs_uri = normalize_to_gs_bucket_uri(uri)
    bucket_name, path = parse_gcs_url(gs_uri)

    storage_client = storage.Client(
        project=GOOGLE_CLOUD_PROJECT, client_info=ClientInfo(user_agent=USER_AGENT)
    )
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(path)

    # This is the most direct way to get the file's content as bytes
    file_bytes = blob.download_as_bytes()

    print(f"File gs://{bucket_name}/{path} downloaded as bytes.")
    return file_bytes


def get_gcs_uri_from_bucket_name(bucket_name) -> str:
    """Returns a GCS URI for a given bucket name.

    Args:
        bucket_name (str): The name of the GCS bucket.

    Returns:
        str: The GCS URI (e.g., 'gs://project_id/bucket_name').
    """

    uri = f"gs://{bucket_name}"
    return uri


def normalize_to_gs_bucket_uri(path: str) -> str:
    """Normalizes a GCS path, URL, or bucket/object path to a GCS object URI.

    Args:
        path: The input string representing the GCS location.

    Returns:
        The normalized GCS object URI in the format 'gs://<bucket-name>/<path-to-file>'.
    """
    if path.startswith("gs://"):
        # It's already in the correct format, but we should unquote the path
        # to handle any percent-encoded characters from sources like signed URLs.
        parsed = urlparse(path)
        return urlunparse(("gs", parsed.netloc, unquote(parsed.path), "", "", ""))

    elif path.startswith("http://") or path.startswith("https://"):
        parsed_url = urlparse(path)

        # GCS HTTP paths are typically /<bucket>/<object>
        # Split the path into components
        path_parts = parsed_url.path.strip("/").split("/", 1)
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GCS HTTP URL format: {path}")

        bucket_name = path_parts[0]
        object_path = path_parts[1]

        # Decode the object path to restore spaces
        decoded_path = unquote(object_path)

        return f"gs://{bucket_name}/{decoded_path}"

    else:
        # Assume it's a bucket/object path
        path_parts = path.strip("/").split("/", 1)
        if len(path_parts) < 2:
            # Handle cases like "my-bucket" which should be converted to "gs://my-bucket"
            bucket_name = path_parts[0] if path_parts else ""
            return f"gs://{bucket_name}"

        bucket_name = path_parts[0]
        object_path = path_parts[1]

        # No URL decoding needed for this path style
        return f"gs://{bucket_name}/{object_path}"


def normalize_to_authenticated_url(path: str) -> str:
    """Normalizes a GCS path or public URL to a full authenticated URL.

    This function takes a string representing a GCS object and returns a
    full 'storage.cloud.google.com' URL for it. It can handle:
    1. A GCS URI (e.g., 'gs://my-bucket/folder/file.txt')
    2. A public GCS HTTP URL (e.g., 'https://storage.googleapis.com/my-bucket/folder/file.txt')
    3. A path that includes the bucket and object (e.g., 'my-bucket/folder/file.txt')

    Args:
        path: The input string representing the GCS object location.

    Returns:
        The full authenticated URL in the format
        'https://storage.cloud.google.com/<bucket-name>/<path-to-file>'.
    """
    uri = normalize_to_gs_bucket_uri(path)
    return uri.replace("gs://", GCS_AUTHENTICATED_DOMAIN)


def download_bytes_from_gcs(uri: str) -> bytes:
    """Downloads a file from Google Cloud Storage and returns its content as bytes.

    Args:
        uri (str): The GCS URI of the object (e.g., "gs://bucket_name/path/to/file").

    Returns:
        bytes: The raw content of the file.
    """
    gs_uri = normalize_to_gs_bucket_uri(uri)
    bucket_name, path = parse_gcs_url(gs_uri)

    storage_client = storage.Client(
        project=GOOGLE_CLOUD_PROJECT, client_info=ClientInfo(user_agent=USER_AGENT)
    )
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(path)

    # This is the most direct way to get the file's content as bytes
    file_bytes = blob.download_as_bytes()

    print(f"File gs://{bucket_name}/{path} downloaded as bytes.")
    return file_bytes
