from pyspark.sql import SparkSession
import os

def run():
    spark = SparkSession.builder \
        .appName("CheckMinIO") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    try:
        # Check raw bucket
        with open("/app/minio_result.txt", "w") as f:
            f.write("Checking s3a://myminio/raw/shop_events...\n")
            try:
                df = spark.read.parquet("s3a://raw/shop_events")
                cnt = df.count()
                f.write(f"Count: {cnt}\n")
                if cnt > 0:
                    rows = df.take(5)
                    f.write(f"Sample: {rows}\n")
            except Exception as e:
                f.write(f"Error reading: {e}\n")
    except Exception as e:
        print(f"Setup Error: {e}")

if __name__ == "__main__":
    run()
