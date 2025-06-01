import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Groq API Configuration
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    # Default model for Groq
    GROQ_MODEL = "llama-3.3-70b-versatile"