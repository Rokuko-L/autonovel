import httpx
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
model = "mmf/mimo-auto"

headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

payload = {
    "model": model,
    "max_tokens": 1000,
    "messages": [{"role": "user", "content": "Hello, write one paragraph."}],
}

print(f"Base URL: {base_url}")
print(f"Model: {model}")
print(f"Headers: {headers}")

try:
    with httpx.Client() as client:
        resp = client.post(
            f"{base_url.rstrip('/')}/v1/messages",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        print(f"Status Code: {resp.status_code}")
        print("Response Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
        print("Response Content:")
        import utils
        parsed_text = utils.extract_text_from_response(resp)
        print("="*40)
        print("Parsed Text:")
        print(repr(parsed_text))
except Exception as e:
    print(f"Error occurred: {e}", file=sys.stderr)
