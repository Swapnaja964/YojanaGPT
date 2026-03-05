# local_llm_test.py
from transformers import pipeline
from dotenv import load_dotenv
import torch

def test_local_llm():
    print("🚀 Setting up local language model...")
    
    try:
        # Use a small, fast model for testing
        model_name = "distilgpt2"  # Small version of GPT-2 that runs locally
        
        print(f"Loading {model_name}... (this may take a few minutes on first run)")
        
        # Enable CPU offloading if you have limited RAM
        device = 0 if torch.cuda.is_available() else -1  # Use GPU if available, else CPU
        
        # Load the model with reduced precision to save memory
        generator = pipeline(
            'text-generation', 
            model=model_name,
            device=device,
            torch_dtype=torch.float16 if device == 0 else None
        )
        
        # Generate text
        print("\n🤖 Model is ready! Generating text...")
        result = generator(
            "Hello, I'm a language model,", 
            max_length=50, 
            num_return_sequences=1,
            pad_token_id=generator.tokenizer.eos_token_id  # Ensure proper termination
        )
        
        print("\n✅ Success!")
        print("Generated text:", result[0]['generated_text'])
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you have PyTorch installed: pip install torch")
        print("2. Install the transformers library: pip install transformers")
        print("3. For better performance, consider installing with GPU support")
        print("4. If you're running out of memory, try a smaller model like 'gpt2' or 'distilgpt2'")
        return False

if __name__ == "__main__":
    load_dotenv(override=True)
    test_local_llm()
