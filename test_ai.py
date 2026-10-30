
import os
from dotenv import load_dotenv
from google import genai

# Load our private API key
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("API key not found! Check your .env file.")

# Connect to Google's AI service
client = genai.Client(api_key=api_key)

# Ask Gemma to respond as a Mars rover copilot
response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents=(
        "You are the AI copilot aboard a Mars rover. "
        "Our rover has 85% battery and needs to collect "
        "three scientific samples. Give a short mission briefing."
    )
)

print("\n🚀 MARSOPS AI COPILOT")
print("------------------------")
print(response.text)
