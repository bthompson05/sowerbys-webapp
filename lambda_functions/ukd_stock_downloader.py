import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen

import boto3


s3 = boto3.client("s3")


def lambda_handler(event, context):
    csv_url = os.environ["UKD_STOCK_CSV_URL"]
    bucket_name = os.environ["S3_BUCKET_NAME"]
    s3_prefix = os.environ.get("S3_PREFIX", "").strip("/")
    file_name = f"{datetime.now(timezone.utc):%Y%m%d}.csv"
    s3_key = f"{s3_prefix}/{file_name}" if s3_prefix else file_name

    request = Request(csv_url, headers={"User-Agent": "Sowerbys-UKD-Stock-Downloader/1.0"})
    with urlopen(request, timeout=60) as response:
        csv_bytes = response.read()

    s3.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=csv_bytes,
        ContentType="text/csv",
    )

    return {
        "statusCode": 200,
        "bucket": bucket_name,
        "key": s3_key,
        "bytes_downloaded": len(csv_bytes),
    }
