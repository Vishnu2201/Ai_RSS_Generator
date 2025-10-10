import requests
import os

BASE_URL = os.getenv("BASE_URL", "https://yourapp.onrender.com")

def main():
    try:
        res = requests.get(f"{BASE_URL}/refresh", timeout=120)
        print("Refresh Response:", res.text)
    except Exception as e:
        print("Error during refresh:", e)

if __name__ == "__main__":
    main()
