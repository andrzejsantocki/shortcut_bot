import requests
import json
import  os
from dotenv import load_dotenv

def sync_local_to_cloud():
    """
    Reads the data from the local shortcuts.json file and updates the cloud.
    """
    # 1. Read the local shortcuts.json file
    try:
        with open('shortcuts.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: shortcuts.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from shortcuts.json.")
        return

    # 2. Update the cloud with the data from the local file
    BIN_URL = os.getenv("BIN_URL", '')
    MASTER_KEY = os.getenv("MASTER_KEY",'') 
    headers = {
        'Content-Type': 'application/json',
        'X-Master-Key': MASTER_KEY
    }

    try:
        response = requests.put(BIN_URL, headers=headers, json=data)
        response.raise_for_status()
        print("Successfully synced local data to the cloud.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    sync_local_to_cloud()
