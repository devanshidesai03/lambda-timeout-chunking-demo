import asyncio
import logging
import time
from fastapi import FastAPI
import inngest
import inngest.fast_api


# ----------------------------
# Inngest Client
# ----------------------------
inngest_client = inngest.Inngest(
    app_id="fast_api_example",
    logger=logging.getLogger("uvicorn"),
)

app = FastAPI()


# ============================================================
# 1) BAD FUNCTION (single long run)
# Simulates Lambda timeout issue
# Runs once only (no retries)
# ============================================================
@inngest_client.create_function(
    fn_id="bad_long_job",
    trigger=inngest.TriggerEvent(event="demo/bad_long_job"),
    retries=0,  # ✅ important: fail once and stop
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

        # Simulate Lambda timeout killing the function
        if time.time() - start_time > fake_lambda_timeout:
            raise Exception("❌ Simulated Lambda timeout (15 min limit demo)")

    ctx.logger.info("BAD job finished successfully")
    return "done"


# ============================================================
# 2) START JOB FUNCTION (creates chunks)
# This finishes quickly and creates many chunk events
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

        # ✅ Correct way to publish events in your SDK version
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
# 3) WORKER FUNCTION (processes 1 chunk)
# Each chunk is a separate run -> solves Lambda 15 min issue
# ============================================================
@inngest_client.create_function(
    fn_id="process_chunk",
    trigger=inngest.TriggerEvent(event="demo/process_chunk"),
)
async def process_chunk(ctx: inngest.Context) -> str:
    start = ctx.event.data["start"]
    end = ctx.event.data["end"]

    ctx.logger.info(f"Processing chunk {start} -> {end}")

    # Simulate work (DB/API/file processing)
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
    [bad_long_job, start_job, process_chunk],
)
