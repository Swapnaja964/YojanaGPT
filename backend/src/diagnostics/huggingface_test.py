# huggingface_test.py
import os
import requests
from dotenv import load_dotenv

def test_huggingface():
    # 1. Load environment variables
    load_dotenv(override=True)
    
    # 2. Get API key (optional for some models)
    api_key = os.getenv("HUGGINGFACE_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    
    try:
        # 3. Test with the new router endpoint
        API_URL = "https://router.huggingface.co/gpt2/generation"
        
        print("🔄 Testing Hugging Face API...")
        
        # Try with the new endpoint first
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": "Hello, I'm a language model,", "parameters": {"max_new_tokens": 50}}
        )
        
        # If that fails, try the inference API with a different model
        if response.status_code != 200:
            print("Trying alternative model...")
            response = requests.post(
                "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-125m",
                headers=headers,
                json={"inputs": "Hello, I'm a language model,"}
            )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0 and 'generated_text' in result[0]:
                print("\n✅ Success!")
                print("Response:", result[0]['generated_text'])
            else:
                print("\n✅ Success!")
                print("Response:", result)
            return True
        else:
            print(f"\n❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_huggingface()
