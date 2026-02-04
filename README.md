Lambda Timeout Chunking Demo
FastAPI + Inngest (Local) + AWS SAM + SQS (Cloud)
This project demonstrates a real-world AWS Lambda architecture for handling long-running jobs that would
normally hit the 15-minute Lambda timeout.
It includes:
- Local version (FastAPI + Inngest) to understand the chunking concept
- Cloud version (AWS SAM + SQS + Worker Lambda) to run it in production style
- A simple Inngest trigger function that calls AWS /start
■ Why this exists (The Problem)
AWS Lambda has a hard maximum runtime of 15 minutes per invocation.
So if your job takes longer (example: processing thousands of records, refreshing rates, importing files, calling
APIs), it will:
- timeout
- fail
- possibly retry incorrectly
- waste compute time
■ Solution Used Here (Chunking Pattern)
Instead of one long Lambda run, we use a common production pattern:
1) Starter Lambda (Fast)
- Creates chunk jobs
- Pushes them into SQS
- Finishes quickly
2) SQS Queue (Buffer)
- Stores chunk jobs reliably
- Supports retries automatically
- Allows scaling
3) Worker Lambda (Chunk Processor)
- Processes 1 chunk per invocation
- Each run is small and safe
- Can scale horizontally
4) DLQ (Dead Letter Queue)
- Stores failed chunk messages
- Prevents infinite retries
- Helps debugging
■ Architecture (Flow)
Inngest Event
|
v
FastAPI Inngest Function (triggerawssamjob)
|
v
API Gateway POST /start
|
v
Starter Lambda ---> SQS Queue ---> Worker Lambda
|
v
DLQ
■ Project Structure
demo-inngest/
■
■■■ main.py
■■■ requirements.txt
■■■ README.md
■
■■■ aws/
■■■ template.yaml
■
■■■ starter/
■ ■■■ app.py
■ ■■■ requirements.txt
■
■■■ worker/
■■■ app.py
■■■ requirements.txt
■ What Each File Does
main.py
Contains all Inngest functions and FastAPI server.
Includes:
- badlongjob
Simulates a long-running Lambda timeout problem.
- startjob
Demonstrates chunking locally using Inngest events.
- processchunk
Processes one chunk locally.
- triggerawssamjob
Calls the AWS /start endpoint (Starter Lambda API Gateway).
aws/template.yaml
AWS SAM template that creates:
- API Gateway route: POST /start
- Starter Lambda
- Worker Lambda
- SQS Queue + DLQ
- IAM permissions for sending and polling SQS
aws/starter/app.py
Starter Lambda code:
- reads TOTALITEMS and CHUNKSIZE
- creates chunk messages
- sends them to SQS
aws/worker/app.py
Worker Lambda code:
- triggered automatically by SQS
- processes one chunk at a time
- logs progress into CloudWatch
■■ Local Development (FastAPI + Inngest)
■ Requirements
- Python 3.11+
- Node.js 18+
- Inngest CLI (runs using npx)
- pip
1) Install dependencies
From project root:
cd demo-inngest
pip install -r requirements.txt
2) Run FastAPI dev server
PowerShell:
cd .\demo-inngest
$env:INNGESTDEV=1; uvicorn main:app --reload
3) Run Inngest dev server
In another terminal:
npx --ignore-scripts=false inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
4) Trigger local functions
From Inngest UI (Dev Server), trigger events:
Timeout demo
demo/badlongjob
Chunking demo (local)
demo/startjob
This will publish multiple:
demo/processchunk
■■ Cloud Deployment (AWS SAM + SQS)
■ Requirements
Install:
- AWS CLI
- AWS SAM CLI
- Python 3.11
- AWS account configured locally
Verify AWS login:
aws sts get-caller-identity
1) Deploy using SAM
Go to AWS folder:
cd aws
Build:
sam build
Deploy:
sam deploy --guided
During guided deploy:
- Allow SAM to create IAM roles → YES
- Save arguments to samconfig.toml → YES
2) After deploy (Expected)
You will see in AWS Console:
- 2 Lambda functions:
- lambda-timeout-demo-starter
- lambda-timeout-demo-worker
- 2 queues:
- main SQS queue
- DLQ
- API Gateway endpoint like:
https://xxxx.execute-api.eu-north-1.amazonaws.com/Prod/start
■ Testing AWS from Terminal
PowerShell:
curl.exe -X POST "https://YOURAPI.execute-api.eu-north-1.amazonaws.com/Prod/start"
Expected output:
{
"message": "Job started successfully",
"totalitems": 500,
"chunksize": 50,
"chunkscreated": 10
}
■ Testing AWS from Inngest (Recommended)
Trigger this Inngest event:
demo/triggerawssamjob
That event runs triggerawssamjob in main.py.
■ Viewing Logs in CloudWatch
Starter Lambda logs:
/aws/lambda/lambda-timeout-demo-starter
Worker Lambda logs:
/aws/lambda/lambda-timeout-demo-worker
■ .env for Cloud (Important)
In cloud deployments, environment variables are stored in AWS Lambda settings.
But locally, you can store them in .env.
Create a file:
.env
AWSSTARTURL=https://YOURAPI.execute-api.eu-north-1.amazonaws.com/Prod/start
Then in PowerShell before running uvicorn:
$env:AWSSTARTURL="https://YOURAPI.execute-api.eu-north-1.amazonaws.com/Prod/start"
■ Advantages of This Architecture
- No Lambda timeout failures
- Automatic retries per chunk
- Parallel chunk processing
- Better fault tolerance
- Easier debugging (chunk logs)
- Works perfectly with Inngest orchestration
- Production-ready approach
■ Cleanup (Delete AWS Stack)
sam delete --stack-name lambda-timeout-demo
■ Summary
1. Never run long jobs in one Lambda
2. Chunk + Queue + Worker is the correct scalable solution
