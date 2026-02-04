import json
import time


def lambda_handler(event, context):
    # SQS triggers Lambda with Records
    for record in event["Records"]:
        body = json.loads(record["body"])
        start = body["start"]
        end = body["end"]

        print(f"Processing chunk: {start} -> {end}")

        # Simulate work per item
        for i in range(start, end):
            time.sleep(0.2)

        print(f"Finished chunk: {start} -> {end}")

    return {"status": "ok"}
