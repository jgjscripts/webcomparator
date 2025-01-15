from openai import OpenAI
import logging

class ContentComparator:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def preprocess_text(self, text):
        """Preprocess text for comparison"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Convert to lowercase for case-insensitive comparison
        text = text.lower()
        # Remove common punctuation variations
        text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
        return text

    def compare_contents(self, text1, text2):
        try:
            # Preprocess texts
            processed_text1 = self.preprocess_text(text1)
            processed_text2 = self.preprocess_text(text2)

            # Check for exact match after preprocessing
            if processed_text1 == processed_text2:
                return {
                    'score': '100',
                    'analysis': 'The contents are exactly identical (ignoring case and formatting).'
                }

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a precise content comparison expert. 
                    Follow these rules strictly:
                    1. If the texts are identical or only differ in whitespace, score must be 100
                    2. If the texts contain the same information but slightly different wording, score should be 95-99
                    3. For minor differences, score should be 90-94
                    4. For significant differences, score should be below 90
                    Be very precise in your scoring."""},
                    {"role": "user", "content": f"First provide a similarity score (just the number 0-100) on the first line, then on subsequent lines provide detailed analysis of the key differences:\n\nText 1: {text1}\n\nText 2: {text2}"}
                ],
                temperature=0.3  # Make the model more deterministic
            )
            
            result = response.choices[0].message.content
            lines = result.split('\n', 1)
            score = lines[0].strip().rstrip('%')  # Remove % if present
            analysis = lines[1].strip() if len(lines) > 1 else ""
            
            # Double-check the score for very similar content
            if text1.strip() == text2.strip():
                score = '100'
                analysis = 'The contents are exactly identical.'
            
            return {
                'score': score,
                'analysis': analysis
            }
            
        except Exception as e:
            logging.error(f"Error in comparison: {str(e)}")
            return {
                'score': '0',
                'analysis': f"Error in comparison: {str(e)}"
            }

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Example usage of ContentComparator
    comparator = ContentComparator(os.getenv('OPENAI_API_KEY'))
    
    # Example texts to compare
    text1 = "Python is a high-level programming language known for its simplicity."
    text2 = "Python is a programming language that emphasizes code readability."
    
    print("Testing ContentComparator...")
    print("\nComparing texts:")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    
    result = comparator.compare_contents(text1, text2)
    print("\nComparison Result:")
    print(result) 