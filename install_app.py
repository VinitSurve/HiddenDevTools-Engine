import requests
import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip()

def install_app_on_page():
    print("Installing App on the Facebook Page to enable live Instagram Webhooks...")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/subscribed_apps"
    
    # We omit 'messages' to avoid the OAuth error, we just need the app INSTALLED.
    # The actual 'comments' routing is handled by the Instagram Webhook config in the dashboard.
    payload = {
        "subscribed_fields": "feed",
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Success! The App is now installed on your Facebook Page.")
        print(response.json())
    else:
        print(f"Failed. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    install_app_on_page()
