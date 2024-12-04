from typing import Dict, Any
from .base import BaseProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider
from .gemini_provider import GeminiProvider

def get_provider(provider_name: str, config: Dict[str, Any]) -> BaseProvider:
    """Get the appropriate provider instance based on configuration"""
    providers = {
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "gemini": GeminiProvider
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")
        
    provider_config = config.get(provider_name, {})
    if not provider_config.get("enabled", False):
        raise ValueError(f"Provider {provider_name} is not enabled")
        
    return providers[provider_name](provider_config) 