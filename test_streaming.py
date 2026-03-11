import asyncio
import json
import requests

def test_streaming():
    url = "http://localhost:8000/generate"
    data = {
        "topic": "Test Research Topic",
        "level": "Academic",
        "format": "IEEE Double Column"
    }
    
    print(f"Connecting to {url}...")
    try:
        # We don't use stream=True with requests for SSE easily in a simple script
        # but we can check if the response headers are correct
        response = requests.post(url, data=data, stream=True)
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers.get('Content-Type')}")
        
        count = 0
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    event = json.loads(decoded_line[6:])
                    print(f"Event {count}: {event['type']}")
                    if event['type'] == 'progress':
                        print(f"  Step: {event['data']['step']}, Status: {event['data']['status']}")
                    count += 1
                if count >= 5: # Just check first 5 events
                    break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_streaming()
