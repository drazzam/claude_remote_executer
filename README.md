# Claude Remote Executor

## Overview

**Claude Remote Executor** is a system that allows Claude AI to overcome its runtime limitations by connecting to a Google Colab instance via HTTP. This enables Claude to:

- Download large files (30GB+) that exceed Claude's disk limits
- Run long computations without timeout (up to 12 hours)
- Process data that exceeds Claude's memory limits
- Persist results to Google Drive
- Access GPU resources for ML/DL tasks

### Architecture

```
┌─────────────────────────┐         HTTPS (ngrok)        ┌─────────────────────────────┐
│   Claude AI Runtime     │  ◄─────────────────────────► │   Google Colab Instance     │
│                         │                              │                             │
│  • Limited disk (~10GB) │      POST /execute           │  • 107GB disk               │
│  • ~5 min timeout       │      POST /bash              │  • 12+ hour runtime         │
│  • Limited RAM          │      POST /download          │  • 12-25GB RAM              │
│  • No persistent storage│      GET /ls, /disk, /health │  • Google Drive access      │
│                         │                              │  • Optional GPU (T4/V100)   │
└─────────────────────────┘                              └─────────────────────────────┘
```

---

## Quick Start for Claude

### Step 1: User Setup (One-time)

The user needs to:

1. **Get a free ngrok token**: https://dashboard.ngrok.com/get-started/your-authtoken
2. **Open Google Colab**: https://colab.research.google.com
3. **Run the server notebook** (provided below in [Colab Notebook Code](#colab-notebook-code))
4. **Share the ngrok URL** with Claude (looks like `https://xxxx.ngrok-free.app`)

### Step 2: Claude Connection

Once the user provides the ngrok URL, Claude can connect using this code:

```python
import httpx

BASE_URL = "https://XXXX.ngrok-free.app"  # Replace with user's URL
client = httpx.Client(timeout=300)

# Test connection
response = client.get(f"{BASE_URL}/health")
print(response.json())
# Expected: {'status': 'healthy', 'cpu_percent': ..., 'memory_percent': ..., 'disk_free_gb': ...}
```

---

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check server status and system resources |
| `/` | GET | Server info and available endpoints |
| `/execute` | POST | Execute Python code |
| `/bash` | POST | Execute bash commands |
| `/download` | POST | Download file from URL |
| `/ls` | GET | List directory contents |
| `/disk` | GET | Get disk usage information |

---

### `GET /health`

Check if the remote executor is online and get system statistics.

**Response:**
```json
{
  "status": "healthy",
  "cpu_percent": 5.2,
  "memory_percent": 12.4,
  "disk_free_gb": 86.54
}
```

---

### `POST /execute`

Execute Python code on the remote Colab instance.

**Request Body:**
```json
{
  "code": "print('Hello from Colab!')",
  "timeout": 300
}
```

**Response:**
```json
{
  "success": true,
  "stdout": "Hello from Colab!\n",
  "stderr": "",
  "result": null,
  "error": null
}
```

**Example - Data Processing:**
```python
response = client.post(f"{BASE_URL}/execute", json={
    "code": """
import pandas as pd
import numpy as np

# Create sample data
df = pd.DataFrame(np.random.randn(1000, 4), columns=['A', 'B', 'C', 'D'])
print(f"Shape: {df.shape}")
print(df.describe())
"""
})
print(response.json()['stdout'])
```

---

### `POST /bash`

Execute bash commands on the remote Colab instance.

**Request Body:**
```json
{
  "command": "ls -la /content",
  "timeout": 300
}
```

**Response:**
```json
{
  "success": true,
  "returncode": 0,
  "stdout": "total 12\ndrwxr-xr-x 1 root root 4096 ...",
  "stderr": ""
}
```

**Example:**
```python
response = client.post(f"{BASE_URL}/bash", json={
    "command": "pip install transformers -q && python -c \"import transformers; print(transformers.__version__)\""
})
print(response.json()['stdout'])
```

---

### `POST /download`

Download a file from URL to the remote Colab instance.

**Request Body:**
```json
{
  "url": "https://example.com/large-file.zip",
  "destination": "/content/downloads",
  "filename": "custom_name.zip"
}
```

**Response:**
```json
{
  "success": true,
  "filepath": "/content/downloads/custom_name.zip",
  "size_mb": 1234.56
}
```

**Example - Download to Google Drive:**
```python
response = client.post(f"{BASE_URL}/download", json={
    "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data",
    "destination": "/content/drive/MyDrive/datasets",
    "filename": "iris.csv"
})
result = response.json()
if result['success']:
    print(f"Downloaded: {result['filepath']} ({result['size_mb']} MB)")
```

---

### `GET /ls`

List directory contents.

**Query Parameters:**
- `path` (optional): Directory path to list (default: `/content`)

**Response:**
```json
{
  "success": true,
  "path": "/content",
  "items": [
    {"name": "drive", "is_dir": true, "size": null},
    {"name": "sample_data", "is_dir": true, "size": null},
    {"name": "file.txt", "is_dir": false, "size": 1234}
  ]
}
```

**Example:**
```python
response = client.get(f"{BASE_URL}/ls", params={"path": "/content/drive/MyDrive"})
for item in response.json()['items']:
    icon = "📁" if item['is_dir'] else "📄"
    print(f"{icon} {item['name']}")
```

---

### `GET /disk`

Get disk usage information.

**Response:**
```json
{
  "total_gb": 107.72,
  "used_gb": 21.16,
  "free_gb": 86.54,
  "percent_used": 19.6
}
```

---

## Helper Functions for Claude

Here's a complete helper module Claude can use:

```python
import httpx
from typing import Optional, Dict, Any

class RemoteExecutor:
    """Client for Claude Remote Executor on Google Colab"""
    
    def __init__(self, base_url: str, timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=timeout)
    
    def health(self) -> Dict[str, Any]:
        """Check server health and resources"""
        return self.client.get(f"{self.base_url}/health").json()
    
    def execute(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute Python code remotely"""
        return self.client.post(
            f"{self.base_url}/execute",
            json={"code": code, "timeout": timeout}
        ).json()
    
    def bash(self, command: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute bash command remotely"""
        return self.client.post(
            f"{self.base_url}/bash",
            json={"command": command, "timeout": timeout}
        ).json()
    
    def download(self, url: str, destination: str = "/content/downloads",
                 filename: Optional[str] = None) -> Dict[str, Any]:
        """Download file from URL to Colab"""
        payload = {"url": url, "destination": destination}
        if filename:
            payload["filename"] = filename
        return self.client.post(f"{self.base_url}/download", json=payload).json()
    
    def ls(self, path: str = "/content") -> Dict[str, Any]:
        """List directory contents"""
        return self.client.get(f"{self.base_url}/ls", params={"path": path}).json()
    
    def disk(self) -> Dict[str, Any]:
        """Get disk usage"""
        return self.client.get(f"{self.base_url}/disk").json()


# Usage Example:
# executor = RemoteExecutor("https://xxxx.ngrok-free.app")
# result = executor.execute("print('Hello!')")
# print(result['stdout'])
```

---

## Colab Notebook Code

The user needs to run this in Google Colab. Provide this as a notebook or have them run each cell:

### Cell 1: Install Dependencies
```python
!pip install fastapi uvicorn pyngrok -q
print("✓ Dependencies installed")
```

### Cell 2: Set ngrok Token
```python
# Get your free token from: https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTH_TOKEN = "YOUR_NGROK_TOKEN_HERE"  # User replaces this
```

### Cell 3: Mount Google Drive (Optional but Recommended)
```python
from google.colab import drive
drive.mount('/content/drive')
print("✓ Google Drive mounted at /content/drive")
```

### Cell 4: Create the Server
```python
import os
import sys
import json
import traceback
import subprocess
from io import StringIO
from typing import Optional, Dict, Any
from contextlib import redirect_stdout, redirect_stderr

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Claude Remote Executor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

execution_namespace = {"__builtins__": __builtins__}

class CodeRequest(BaseModel):
    code: str
    timeout: Optional[int] = 300

class BashRequest(BaseModel):
    command: str
    timeout: Optional[int] = 300

class DownloadRequest(BaseModel):
    url: str
    destination: str = "/content/downloads"
    filename: Optional[str] = None

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Claude Remote Executor",
        "endpoints": ["/execute", "/bash", "/download", "/ls", "/disk", "/health"]
    }

@app.get("/health")
def health():
    import psutil
    return {
        "status": "healthy",
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
    }

@app.post("/execute")
def execute_code(request: CodeRequest):
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    result = None
    error = None
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            try:
                exec(request.code, execution_namespace)
                lines = request.code.strip().split('\n')
                if lines:
                    last_line = lines[-1].strip()
                    if last_line and not any(last_line.startswith(kw) for kw in 
                        ['import', 'from', 'def', 'class', 'if', 'for', 'while', 'with', 'try', '#', 'print']):
                        try:
                            result = eval(last_line, execution_namespace)
                        except:
                            pass
            except SyntaxError:
                result = eval(request.code, execution_namespace)
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    
    return {
        "success": error is None,
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "result": repr(result) if result is not None else None,
        "error": error
    }

@app.post("/bash")
def execute_bash(request: BashRequest):
    try:
        result = subprocess.run(
            request.command, shell=True, capture_output=True,
            text=True, timeout=request.timeout
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {request.timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/download")
def download_file(request: DownloadRequest):
    os.makedirs(request.destination, exist_ok=True)
    filename = request.filename or request.url.split('/')[-1].split('?')[0]
    filepath = os.path.join(request.destination, filename)
    
    try:
        result = subprocess.run(
            f'wget -q -O "{filepath}" "{request.url}"',
            shell=True, capture_output=True, text=True, timeout=3600
        )
        if os.path.exists(filepath):
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            return {"success": True, "filepath": filepath, "size_mb": round(size_mb, 2)}
        else:
            return {"success": False, "error": "Download failed", "stderr": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/ls")
def list_directory(path: str = "/content"):
    try:
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            size = os.path.getsize(item_path) if not is_dir else None
            items.append({"name": item, "is_dir": is_dir, "size": size})
        return {"success": True, "path": path, "items": items}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/disk")
def disk_usage():
    import shutil
    total, used, free = shutil.disk_usage("/")
    return {
        "total_gb": round(total / (1024**3), 2),
        "used_gb": round(used / (1024**3), 2),
        "free_gb": round(free / (1024**3), 2),
        "percent_used": round(used / total * 100, 1)
    }

print("✓ FastAPI server created")
```

### Cell 5: Start the Server (Keep Running)
```python
import asyncio
import threading
import uvicorn
from pyngrok import ngrok, conf

# Configure ngrok
conf.get_default().auth_token = NGROK_AUTH_TOKEN

# Kill any existing tunnels
ngrok.kill()

PORT = 8000
public_url = ngrok.connect(PORT, "http").public_url

print("=" * 60)
print("🚀 CLAUDE REMOTE EXECUTOR IS RUNNING!")
print("=" * 60)
print(f"\n📡 PUBLIC URL: {public_url}")
print(f"\n📋 Share this URL with Claude to enable remote execution")
print(f"\n📖 API Docs: {public_url}/docs")
print("=" * 60)

def run_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

print("✓ Server started. Keep this cell running!")

import time
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("\n🛑 Server stopped")
    ngrok.kill()
```

---

## Common Use Cases

### 1. Download Large Dataset

```python
# Download a large dataset that would exceed Claude's disk limits
result = executor.download(
    url="https://example.com/large-dataset.zip",
    destination="/content/drive/MyDrive/datasets",
    filename="dataset.zip"
)
print(f"Downloaded: {result['filepath']} ({result['size_mb']} MB)")

# Extract it
executor.bash("cd /content/drive/MyDrive/datasets && unzip -o dataset.zip")
```

### 2. Process Large CSV File

```python
result = executor.execute("""
import pandas as pd

# Load large CSV (would crash Claude's runtime)
df = pd.read_csv('/content/drive/MyDrive/datasets/large_file.csv')

print(f"Shape: {df.shape}")
print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")
print(f"Columns: {list(df.columns)}")

# Process and save results
summary = df.describe()
summary.to_csv('/content/drive/MyDrive/results/summary.csv')
print("Summary saved to Google Drive")
""")
print(result['stdout'])
```

### 3. Train ML Model

```python
result = executor.execute("""
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# Load data
df = pd.read_csv('/content/drive/MyDrive/datasets/training_data.csv')
X = df.drop('target', axis=1)
y = df['target']

# Split and train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestClassifier(n_estimators=100, n_jobs=-1)
model.fit(X_train, y_train)

# Evaluate
accuracy = accuracy_score(y_test, model.predict(X_test))
print(f"Accuracy: {accuracy:.2%}")

# Save model to Google Drive
joblib.dump(model, '/content/drive/MyDrive/models/rf_model.pkl')
print("Model saved!")
""")
print(result['stdout'])
```

### 4. Install and Use Custom Packages

```python
# Install packages
executor.bash("pip install transformers torch sentencepiece -q")

# Use them
result = executor.execute("""
from transformers import pipeline
classifier = pipeline("sentiment-analysis")
result = classifier("I love using Claude with remote execution!")
print(result)
""")
print(result['stdout'])
```

---

## Troubleshooting

### "ngrok agent session limit" Error

The free ngrok tier allows only 1 simultaneous session. Run this in Colab before Cell 5:

```python
from pyngrok import ngrok
ngrok.kill()
!pkill -f ngrok || true
print("✓ All ngrok sessions killed")
```

Or manually terminate at: https://dashboard.ngrok.com/agents

### Connection Timeout

- Increase timeout: `client = httpx.Client(timeout=600)`
- Check if Colab cell is still running
- Verify the ngrok URL is correct

### "asyncio.run() cannot be called" Error

This means the server code is using the old method. Ensure Cell 5 uses the threaded approach with `asyncio.new_event_loop()`.

### Google Drive Not Accessible

Run Cell 3 to mount Google Drive:
```python
from google.colab import drive
drive.mount('/content/drive')
```

### Code Execution Returns Empty

Check the `error` field in the response:
```python
result = executor.execute("some code")
if not result['success']:
    print(f"Error: {result['error']}")
```

---

## Resource Limits

| Resource | Free Colab | Colab Pro |
|----------|------------|-----------|
| Disk Space | ~107 GB | ~225 GB |
| RAM | 12.7 GB | 25-52 GB |
| GPU | T4 (limited) | T4/V100/A100 |
| Runtime | 12 hours | 24 hours |
| Google Drive | Unlimited* | Unlimited* |

*Based on user's Google Drive quota

---

## Security Notes

1. The ngrok URL is **publicly accessible** - anyone with the URL can execute code
2. The URL changes each time the server restarts
3. Consider adding authentication for sensitive use cases
4. Don't store secrets in executed code - use Colab secrets or environment variables

---

## License

MIT License - Free to use, modify, and distribute.
