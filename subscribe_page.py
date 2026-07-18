import requests
import sys
from settings import FACEBOOK_PAGE_ID, INSTAGRAM_ACCESS_TOKEN, GRAPH_API_VERSION

def subscribe_page():
    if not FACEBOOK_PAGE_ID or not INSTAGRAM_ACCESS_TOKEN:
        print("Error: FACEBOOK_PAGE_ID or INSTAGRAM_ACCESS_TOKEN is missing in .env")
        sys.exit(1)

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/subscribed_apps"
    
    # These fields must match what you subscribed to in the Webhooks dashboard
    payload = {
        "subscribed_fields": "feed,messages,comments",
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }
    
    print(f"Subscribing app to Facebook Page ID: {FACEBOOK_PAGE_ID}...")
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print("✓ Successfully subscribed page to the app!")
        print(response.json())
    else:
        print(f"X Failed to subscribe page. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    subscribe_page()
