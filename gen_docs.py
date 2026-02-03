import google.generativeai as genai

# আপনার API Key এখানে দিন
genai.configure(api_key="YOUR_AI_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_docs():
    with open("falcon_engine.py", "r") as f:
        code = f.read()
    
    prompt = f"Act as a software documenter. Here is my programming language code: {code}. Write a professional README.md explaining how to use it."
    response = model.generate_content(prompt)
    
    with open("README.md", "w") as f:
        f.write(response.text)
    print("📖 AI has successfully generated your documentation!")

if __name__ == "__main__":
    generate_docs()

