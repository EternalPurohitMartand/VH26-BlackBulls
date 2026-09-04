# ml_pipeline/genai_patcher.py
import os
import google.generativeai as genai

def generate_safe_code(filepath, line_number, resource_name):
    """Sends leaking code to Gemini and returns a safely refactored version."""
    
    # ⚠️ For the hackathon, you need to set this environment variable in your terminal:
    # $env:GEMINI_API_KEY="your_actual_api_key_here"
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY environment variable not set.")
        print("Get a free key from Google AI Studio (aistudio.google.com) to use Auto-Fix.")
        return None

    genai.configure(api_key=api_key)
    
    # We use gemini-2.5-flash as it is blazing fast for code refactoring
    model = genai.GenerativeModel('gemini-3.8-flash')

    with open(filepath, 'r', encoding='utf-8') as f:
        original_code = f.read()

    # The Prompt Engineering: Giving the LLM strict boundaries
    prompt = f"""
    You are an expert Python static analysis remediation engine.
    The following Python code has a resource leak detected at line {line_number}.
    The variable '{resource_name}' is not safely closed.
    
    Refactor the code to fix this leak. Use Pythonic best practices, such as a 
    `with` statement (context manager) or a `try...finally` block.
    
    IMPORTANT: Return ONLY the raw, rewritten Python code. Do not include markdown formatting, 
    do not include backticks (```python), and do not add any conversational text. 
    Just the exact code that should replace the file.

    Original Code:
    {original_code}
    """

    try:
        print("  🧠 Consulting GenAI for optimal refactoring...")
        response = model.generate_content(prompt)
        # Strip out any accidental markdown blocks the LLM might try to sneak in
        clean_code = response.text.replace("```python", "").replace("```", "").strip()
        return clean_code
    except Exception as e:
        print(f"  ❌ Failed to generate patch: {e}")
        return None