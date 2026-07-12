import requests
import os
import sys
from dotenv import load_dotenv, set_key

# Load existing environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")

def get_page_token_and_subscribe():
    if not INSTAGRAM_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        print("Missing INSTAGRAM_ACCESS_TOKEN or FACEBOOK_PAGE_ID in .env")
        sys.exit(1)

    print("1. Fetching Page Access Token...")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
    params = {"access_token": INSTAGRAM_ACCESS_TOKEN}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print("Error fetching accounts:")
        print(data)
        sys.exit(1)
        
    page_token = None
    for page in data.get("data", []):
        if str(page.get("id")) == str(FACEBOOK_PAGE_ID):
            page_token = page.get("access_token")
            print(f"Found Page Access Token for Page '{page.get('name')}'!")
            break
            
    if not page_token:
        print(f"Could not find a Page Access Token for Page ID {FACEBOOK_PAGE_ID}.")
        print("Does this User Token have 'pages_show_list' and 'pages_read_engagement' permissions?")
        sys.exit(1)
        
    # Update .env securely
    set_key(env_path, "INSTAGRAM_ACCESS_TOKEN", page_token)
    print("Automatically updated .env with the new Page Access Token!")
    
    print("\n2. Subscribing App to Page for Webhooks...")
    sub_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/subscribed_apps"
    sub_payload = {
        "subscribed_fields": "feed,messages", # "comments" isn't a page field, it's an IG field
        "access_token": page_token
    }
    
    sub_response = requests.post(sub_url, data=sub_payload)
    if sub_response.status_code == 200:
        print("Successfully installed the App on your Facebook Page!")
    else:
        print(f"Failed to subscribe page. Status: {sub_response.status_code}")
        print(sub_response.text)

if __name__ == "__main__":
    get_page_token_and_subscribe()
