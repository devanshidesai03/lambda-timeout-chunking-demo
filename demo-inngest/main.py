import asyncio
import logging
import time
import os

from fastapi import FastAPI
import inngest
import inngest.fast_api
import httpx


# ----------------------------
# Inngest Client
# ----------------------------
inngest_client = inngest.Inngest(
    app_id="fast_api_example",
    logger=logging.getLogger("uvicorn"),
)

app = FastAPI()


# ============================================================
# 0) TRIGGER AWS SAM JOB (Inngest -> AWS API Gateway -> Starter Lambda)
# ============================================================
AWS_START_URL = os.environ.get(
    "AWS_START_URL",
    "https://64ikrf53rg.execute-api.eu-north-1.amazonaws.com/Prod/start",
)

@inngest_client.create_function(
    fn_id="trigger_aws_sam_job",
    trigger=inngest.TriggerEvent(event="demo/trigger_aws_sam_job"),
    retries=0,
)
async def trigger_aws_sam_job(ctx: inngest.Context):
    ctx.logger.info(f"Triggering AWS Starter API: {AWS_START_URL}")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(AWS_START_URL)

    ctx.logger.info(f"AWS response: {r.status_code} {r.text}")

    if r.status_code >= 400:
        raise Exception(f"AWS Starter failed: {r.status_code} {r.text}")

    return {"status_code": r.status_code, "body": r.text}


# ============================================================
# 1) BAD FUNCTION (single long run)
# Simulates Lambda timeout issue
# Runs once only (no retries)
# ============================================================
@inngest_client.create_function(
    fn_id="bad_long_job",
    trigger=inngest.TriggerEvent(event="demo/bad_long_job"),
    retries=0,
)
async def bad_long_job(ctx: inngest.Context) -> str:
    ctx.logger.info("Starting BAD long job...")

    start_time = time.time()
    fake_lambda_timeout = 10  # seconds (demo only)

    total = 500
    for i in range(total):
        await asyncio.sleep(0.2)

        if i % 25 == 0:
            ctx.logger.info(f"BAD job progress: {i}/{total}")

        if time.time() - start_time > fake_lambda_timeout:
            raise Exception("❌ Simulated Lambda timeout (15 min limit demo)")

    ctx.logger.info("BAD job finished successfully")
    return "done"


# ============================================================
# 2) START JOB FUNCTION (creates chunks locally using Inngest events)
# ============================================================
@inngest_client.create_function(
    fn_id="start_job",
    trigger=inngest.TriggerEvent(event="demo/start_job"),
)
async def start_job(ctx: inngest.Context) -> str:
    ctx.logger.info("Starting GOOD job and creating chunks...")

    total = 500
    chunk_size = 50

    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)

        await inngest_client.send(
            inngest.Event(
                name="demo/process_chunk",
                data={"start": start, "end": end},
            )
        )

        ctx.logger.info(f"Queued chunk {start} -> {end}")

    ctx.logger.info("All chunks queued successfully")
    return "chunks_created"


# ============================================================
# 3) WORKER FUNCTION (processes 1 chunk locally)
# ============================================================
@inngest_client.create_function(
    fn_id="process_chunk",
    trigger=inngest.TriggerEvent(event="demo/process_chunk"),
)
async def process_chunk(ctx: inngest.Context) -> str:
    start = ctx.event.data["start"]
    end = ctx.event.data["end"]

    ctx.logger.info(f"Processing chunk {start} -> {end}")

    for i in range(start, end):
        await asyncio.sleep(0.2)

    ctx.logger.info(f"Finished chunk {start} -> {end}")
    return f"chunk_done_{start}_{end}"


# ----------------------------
# Serve Inngest endpoint
# ----------------------------
inngest.fast_api.serve(
    app,
    inngest_client,
    [trigger_aws_sam_job, bad_long_job, start_job, process_chunk],
)
