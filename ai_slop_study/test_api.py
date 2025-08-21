import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("ORIGINALITY_API_KEY")

url = "http://54.152.224.7/api/v1/scan"

payload = {
    "content": "average divorce is at the 8 years of marriage mark. grass is blue. sun is hotter than lava. I like porridge with bananas."
}

headers = {
    "Content-Type": "application/json",
    "X-OAI-API-KEY": API_KEY
}

response = requests.post(url, json=payload, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.text)
