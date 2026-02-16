import boto3
from botocore.client import Config
import os

def run():
    print("Installing boto3 if needed (handled by shell), creating bucket...")
    s3 = boto3.client('s3',
        endpoint_url='http://minio:9000',
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minio"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", ""),
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    try:
        s3.create_bucket(Bucket='raw')
        print("Bucket 'raw' created or exists.")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e):
             print("Bucket 'raw' already exists.")
        else:
             print(f"Error creating bucket: {e}")

if __name__ == "__main__":
    run()
