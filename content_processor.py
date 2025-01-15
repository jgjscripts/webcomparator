from openai import OpenAI
import tiktoken

class ContentProcessor:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"
        self.encoding = tiktoken.encoding_for_model(self.model)

    def prepare_content(self, text, max_tokens=3000):
        """Prepare content for OpenAI analysis by truncating if necessary"""
        if not text:
            return ""
            
        tokens = self.encoding.encode(text)
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
            text = self.encoding.decode(tokens)
        
        return text

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Example usage of ContentProcessor
    processor = ContentProcessor(os.getenv('OPENAI_API_KEY'))
    
    # Example long text
    long_text = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
    """ * 100  # Repeat to make it longer
    
    print("Testing ContentProcessor...")
    print(f"\nOriginal text length: {len(long_text)}")
    
    processed_text = processor.prepare_content(long_text)
    print(f"Processed text length: {len(processed_text)}")
    print("\nFirst 200 characters of processed text:")
    print(processed_text[:200]) 