import hmac
import hashlib
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
META_APP_SECRET = os.getenv("META_APP_SECRET")

if not META_APP_SECRET:
    print("Error: META_APP_SECRET not found in .env")
    exit(1)

payload = {
  "object": "instagram",
  "entry": [
    {
      "id": "17841424886946159",
      "time": 1720543200,
      "changes": [
        {
          "field": "comments",
          "value": {
            "from": {
              "id": "1234567890",
              "username": "test_user"
            },
            "media": {
              "id": "18000000000000000",
              "media_product_type": "FEED"
            },
            "id": "17000000000000000",
            "text": "DEV test comment!"
          }
        }
      ]
    }
  ]
}

payload_bytes = json.dumps(payload).encode('utf-8')
signature = hmac.new(
    key=META_APP_SECRET.encode('utf-8'),
    msg=payload_bytes,
    digestmod=hashlib.sha256
).hexdigest()

headers = {
    'Content-Type': 'application/json',
    'X-Hub-Signature-256': f'sha256={signature}'
}

response = requests.post('http://localhost:8000/webhooks/meta', data=payload_bytes, headers=headers)
print(f"Server responded with: {response.status_code}")
print(response.json())
