import json
import os
import boto3

sqs = boto3.client("sqs")


def lambda_handler(event, context):
    queue_url = os.environ["QUEUE_URL"]
    total_items = int(os.environ.get("TOTAL_ITEMS", "500"))
    chunk_size = int(os.environ.get("CHUNK_SIZE", "50"))

    chunks_created = 0

    for start in range(0, total_items, chunk_size):
        end = min(start + chunk_size, total_items)

        message = {"start": start, "end": end}

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
        )

        chunks_created += 1

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Job started successfully",
                "total_items": total_items,
                "chunk_size": chunk_size,
                "chunks_created": chunks_created,
            }
        ),
    }
