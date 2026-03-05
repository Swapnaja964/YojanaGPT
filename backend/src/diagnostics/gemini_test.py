import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini():
    # 1. Load environment variables
    load_dotenv(override=True)
    
    # 2. Get API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables")
        print("Get your API key from: https://aistudio.google.com/app/apikey")
        return False
    
    try:
        # 3. Configure the API
        genai.configure(api_key=api_key)
        
        # 4. List available models
        print("🔍 Listing available models...")
        models = genai.list_models()
        
        if not models:
            print("❌ No models found. Please check your API key and permissions.")
            return False
            
        print("\nAvailable Models:")
        model_names = []
        for m in models:
            model_name = m.name.split('/')[-1]  # Extract just the model name
            model_names.append(model_name)
            print(f"- {model_name}")
        
        # 5. Try with a model that supports text generation
        text_models = [m for m in model_names if 'gemini' in m.lower() and 'embedding' not in m.lower()]
        
        if not text_models:
            print("❌ No text generation models found.")
            return False
            
        # Try with the first text generation model
        test_model = text_models[0]
        print(f"\n🔄 Testing with model: {test_model}")
        
        try:
            # Initialize the model
            model = genai.GenerativeModel(test_model)
            
            # Generate content
            response = model.generate_content("Say hello and tell me what model you are")
            
            print("\n✅ Success!")
            print("Response:", response.text)
            return True
            
        except Exception as model_error:
            print(f"\n❌ Error with model {test_model}: {str(model_error)}")
            
            # Try with a direct API call as fallback
            print("\n🔄 Trying alternative approach...")
            try:
                response = genai.generate_content(
                    model=test_model,
                    contents=[{"parts": [{"text": "Say hello and tell me what model you are"}]}]
                )
                print("\n✅ Success with alternative approach!")
                print("Response:", response.text)
                return True
            except Exception as alt_error:
                print(f"\n❌ Alternative approach failed: {str(alt_error)}")
                return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you've enabled the Gemini API in Google AI Studio")
        print("2. Check that your API key has the correct permissions")
        print("3. Visit https://ai.google.dev/ for the latest documentation")
        return False

if __name__ == "__main__":
    test_gemini()
