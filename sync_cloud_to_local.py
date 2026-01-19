import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def sync_cloud_to_local():
    """
    Reads the data from jsonbin.io and overwrites the local shortcuts.json file.
    """
    BIN_URL = os.getenv("BIN_URL", '')
    MASTER_KEY = os.getenv("MASTER_KEY",'') 
    headers = {
        'X-Master-Key': MASTER_KEY
    }
    
    try:
        response = requests.get(BIN_URL, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        cloud_data = response.json().get('record')
        
        if cloud_data:
            with open('shortcuts.json', 'w') as f:
                json.dump(cloud_data, f, indent=2)
            print("Successfully synced cloud data to shortcuts.json")
        else:
            print("Error: No record found in the cloud data.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from the cloud response.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":

    sync_cloud_to_local()
