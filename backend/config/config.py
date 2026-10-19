import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY-API-KEY") or os.getenv("TAVILY_API_KEY")
        self.hf_token = os.getenv("HF-TOKEN") or os.getenv("HF_TOKEN")
        self.openai_api_key = os.getenv("OPENAI-API-KEY") or os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI-API-KEY") or os.getenv("GEMINI_API_KEY")
        self.groq_api_key = os.getenv("GROQ-API-KEY") or os.getenv("GROQ_API_KEY")
        self.supabase_url = os.getenv("SUPABASE-URL") or os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE-SECRET-KEY") or os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE-KEY")
        self.pinecone_api_key = os.getenv("PINECONE-API-KEY") or os.getenv("PINECONE_API_KEY")

    def get_tavily_api_key(self) -> str :
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not found")
        return self.tavily_api_key

    def get_hf_token(self) -> str :
        if not self.hf_token:
            raise ValueError("HF_TOKEN not found")
        return self.hf_token

    def get_openai_api_key(self) -> str :
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found")
        return self.openai_api_key

    def get_gemini_api_key(self) -> str :
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found")
        return self.gemini_api_key

    def get_groq_api_key(self) -> str :
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found")
        return self.groq_api_key

    def get_supabase_url(self) -> str :
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL not found")
        return self.supabase_url

    def get_supabase_key(self) -> str :
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY not found")
        return self.supabase_key

    def get_pinecone_api_key(self) -> str :
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY not found")
        return self.pinecone_api_key

settings = Settings()
