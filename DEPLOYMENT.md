# WattWise AI — IBM Cloud Deployment Guide

## Overview

WattWise AI is designed for deployment on **IBM Cloud Code Engine** (fully managed, serverless).
It also supports IBM Cloud Foundry for legacy deployments.
Both approaches are compatible with IBM Cloud **Lite** (free tier) services.

---

## Option A: IBM Cloud Code Engine (Recommended)

### Prerequisites
- IBM Cloud account (free tier is sufficient)
- IBM Cloud CLI installed: https://cloud.ibm.com/docs/cli
- Docker installed (for local image build)
- IBM Container Registry access

---

### Step 1: Install IBM Cloud CLI plugins

```bash
ibmcloud plugin install code-engine
ibmcloud plugin install container-registry
```

### Step 2: Login to IBM Cloud

```bash
ibmcloud login --apikey YOUR_IBM_API_KEY -r au-syd
ibmcloud target -g Default
```

### Step 3: Create a Dockerfile

Create `wattwise_ai/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create required directories
RUN mkdir -p data reports .flask_session

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:create_app()"]
```

### Step 4: Build and push the Docker image

```bash
cd wattwise_ai

# Login to IBM Container Registry
ibmcloud cr login

# Create a namespace (only once)
ibmcloud cr namespace-add wattwise-ns

# Build and push
docker build -t us.icr.io/wattwise-ns/wattwise-ai:latest .
docker push us.icr.io/wattwise-ns/wattwise-ai:latest
```

### Step 5: Deploy to Code Engine

```bash
# Create a project
ibmcloud ce project create --name wattwise-project
ibmcloud ce project select --name wattwise-project

# Deploy the application
ibmcloud ce application create \
  --name wattwise-ai \
  --image us.icr.io/wattwise-ns/wattwise-ai:latest \
  --port 5000 \
  --min-scale 0 \
  --max-scale 3 \
  --env IBM_API_KEY=your_api_key \
  --env PROJECT_ID=your_project_id \
  --env IBM_URL=https://au-syd.ml.cloud.ibm.com \
  --env MODEL_ID=ibm/granite-3-1-8b-base \
  --env FLASK_SECRET_KEY=your_secret_key \
  --env ELECTRICITY_RATE=0.12
```

### Step 6: Get the application URL

```bash
ibmcloud ce application get --name wattwise-ai --output url
```

---

## Option B: IBM Cloud Foundry

### Step 1: Create manifest.yml

```yaml
applications:
  - name: wattwise-ai
    memory: 512M
    instances: 1
    buildpack: python_buildpack
    command: gunicorn --bind 0.0.0.0:$PORT --workers 2 app:create_app()
    env:
      IBM_API_KEY: your_ibm_api_key
      PROJECT_ID: your_project_id
      IBM_URL: https://au-syd.ml.cloud.ibm.com
      MODEL_ID: ibm/granite-13b-instruct-v2
      FLASK_SECRET_KEY: your_secret_key
      ELECTRICITY_RATE: "0.12"
```

### Step 2: Create Procfile

```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 "app:create_app()"
```

### Step 3: Deploy

```bash
ibmcloud cf push
```

---

## Environment Variables Reference

| Variable | Required | Description | Default |
|---|---|---|---|
| `IBM_API_KEY` | Yes | IBM Cloud API key | — |
| `PROJECT_ID` | Yes | watsonx.ai project ID | — |
| `IBM_URL` | Yes | watsonx.ai regional URL | `https://au-syd.ml.cloud.ibm.com` |
| `MODEL_ID` | No | Foundation model ID | `ibm/granite-13b-instruct-v2` |
| `FLASK_SECRET_KEY` | Yes | Flask session secret | `wattwise-dev-secret` |
| `FLASK_DEBUG` | No | Enable debug mode | `False` |
| `ELECTRICITY_RATE` | No | Rate per kWh in USD | `0.12` |
| `CURRENCY_SYMBOL` | No | Currency symbol | `$` |
| `COUNTRY` | No | User's country for AI context | `United States` |

---

## IBM Cloud Services Integration

### IBM Cloud Object Storage (Future)

WattWise AI is pre-designed to integrate with IBM COS for:
- Persistent storage of uploaded datasets
- Storing generated investigation reports as PDFs

To enable, uncomment the COS variables in `.env.example` and implement the COS client in a new `services/cos_service.py`.

```python
import ibm_boto3
from ibm_botocore.client import Config

cos_client = ibm_boto3.client(
    "s3",
    ibm_api_key_id=os.getenv("COS_API_KEY"),
    ibm_service_instance_id=os.getenv("COS_INSTANCE_ID"),
    config=Config(signature_version="oauth"),
    endpoint_url=os.getenv("COS_ENDPOINT"),
)
```

---

## Security Recommendations for Production

1. **Never commit `.env` to version control** — add it to `.gitignore`
2. Use **IBM Cloud Secrets Manager** for credential rotation
3. Set `FLASK_DEBUG=False` in production
4. Use a strong, random `FLASK_SECRET_KEY` (at least 32 characters)
5. Enable HTTPS via IBM Cloud's built-in TLS termination
6. Restrict `MAX_CONTENT_LENGTH` to limit upload sizes

---

## Scaling

Code Engine automatically scales to zero when idle (cost-free on Lite tier).
Set `--min-scale 1` for instant response times if needed.

For high-traffic scenarios, increase `--max-scale` and `--workers` in the gunicorn command.
