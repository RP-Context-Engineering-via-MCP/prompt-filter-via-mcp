import requests
import time
import json

url = "http://localhost:3003/filter"
data = {
    "prompt": "My email is test@example.com and my phone is 555-0199."
}

def test_server():
    for i in range(10):
        try:
            print(f"Attempt {i+1} to connect to {url}...")
            response = requests.post(url, json=data)
            if response.status_code == 200:
                print("Server is ready!")
                print("Response:")
                print(json.dumps(response.json(), indent=2))
                return True
            else:
                print(f"Server returned status code: {response.status_code}")
                print(response.text)
        except requests.exceptions.ConnectionError:
            print("Connection failed. Server might be still starting...")
            time.sleep(5)
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)
    return False

if __name__ == "__main__":
    if test_server():
        print("Test PASSED")
    else:
        print("Test FAILED")
