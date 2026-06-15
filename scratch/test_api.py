import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

models_to_test = [
    "mimo-v2.5",
    "mimo-v2.5-pro",
]

with httpx.Client() as client:
    for model in models_to_test:
        payload = {
            "model": model,
            "max_tokens": 1000,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": "Hi"}],
        }
        print(f"Testing model: {model}")
        try:
            resp = client.post(
                f"{base_url.rstrip('/')}/v1/messages",
                headers=headers,
                json=payload,
                timeout=15,
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Success! Response: {resp.json()['content'][0]['text']}")
            else:
                print(f"Error: {resp.text}")
        except Exception as e:
            print(f"Exception: {e}")
        print("-" * 40)
