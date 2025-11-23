"""
Abstrakcje dla dostawców AI (LLM).

Wspiera:
- OpenAI (Cloud)
- Ollama (Local)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import ollama
import httpx
from openai import OpenAI

from .config import Config


class AIProvider(ABC):
    """Abstrakcyjna klasa bazowa dla dostawców AI."""
    
    @abstractmethod
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Wysyła wiadomość do modelu AI.
        
        Args:
            model: Nazwa modelu
            messages: Lista wiadomości w formacie [{"role": "user", "content": "..."}]
            format: Format odpowiedzi (np. "json")
            options: Opcjonalne opcje (temperature, num_predict, etc.)
            images: Opcjonalna lista ścieżek do obrazów (dla modeli multimodalnych)
            
        Returns:
            Słownik z odpowiedzią modelu
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Sprawdza czy dostawca jest dostępny."""
        pass


class OllamaProvider(AIProvider):
    """Dostawca AI używający lokalnego Ollama."""
    
    def __init__(self, host: str = None, timeout: int = None):
        """
        Inicjalizuje klienta Ollama.
        
        Args:
            host: Adres serwera Ollama (domyślnie z Config)
            timeout: Timeout w sekundach (domyślnie z Config)
        """
        self.host = host or Config.OLLAMA_HOST
        self.timeout = timeout or Config.OLLAMA_TIMEOUT
        
        try:
            timeout_obj = httpx.Timeout(self.timeout, connect=10.0)
            self.client = ollama.Client(host=self.host, timeout=timeout_obj)
        except Exception as e:
            print(f"BŁĄD: Nie można połączyć się z Ollama na {self.host}: {e}")
            self.client = None
    
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Wysyła wiadomość do Ollama."""
        if not self.client:
            raise RuntimeError("Klient Ollama nie jest dostępny")
        
        # Przygotuj wiadomość użytkownika
        user_message = None
        for msg in messages:
            if msg["role"] == "user":
                user_message = msg
                break
        
        if not user_message:
            raise ValueError("Brak wiadomości użytkownika")
        
        # Ollama wymaga osobnego system promptu
        system_message = None
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
                break
        
        # Przygotuj opcje
        ollama_options = {}
        if options:
            ollama_options.update(options)
        
        # Format JSON
        if format == "json":
            ollama_options["format"] = "json"
        
        # Wywołaj API Ollama
        response = self.client.chat(
            model=model,
            messages=messages,
            options=ollama_options if ollama_options else None,
        )
        
        # Ollama zwraca odpowiedź w formacie {"message": {"content": "..."}}
        return response
    
    def is_available(self) -> bool:
        """Sprawdza czy Ollama jest dostępna."""
        if not self.client:
            return False
        try:
            self.client.list()
            return True
        except Exception:
            return False


class OpenAIProvider(AIProvider):
    """Dostawca AI używający OpenAI API."""
    
    def __init__(self, api_key: str = None):
        """
        Inicjalizuje klienta OpenAI.
        
        Args:
            api_key: Klucz API OpenAI (domyślnie z Config)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        if not self.api_key:
            print("OSTRZEŻENIE: Brak klucza API OpenAI (OPENAI_API_KEY).")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
    
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Wysyła wiadomość do OpenAI."""
        if not self.client:
            raise RuntimeError("Klient OpenAI nie jest dostępny (brak klucza API)")
        
        # Przygotuj wiadomości dla OpenAI
        openai_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # OpenAI obsługuje obrazy w wiadomościach użytkownika
            if role == "user" and images:
                # Dla modeli multimodalnych, obrazy są w content jako lista
                content_parts = [{"type": "text", "text": content}]
                for img_path in images:
                    # OpenAI wymaga base64 lub URL, ale możemy użyć file upload
                    # Na razie obsługujemy tylko tekst + obrazy jako base64
                    # W przyszłości można dodać obsługę plików
                    import base64
                    with open(img_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode('utf-8')
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                    })
                openai_messages.append({"role": role, "content": content_parts})
            else:
                openai_messages.append({"role": role, "content": content})
        
        # Przygotuj opcje
        openai_options = {}
        if options:
            # Mapowanie opcji Ollama na OpenAI
            if "temperature" in options:
                openai_options["temperature"] = options["temperature"]
            if "num_predict" in options:
                openai_options["max_tokens"] = options["num_predict"]
        
        # Format JSON (response_format)
        response_format = None
        if format == "json":
            response_format = {"type": "json_object"}
        
        # Wywołaj API OpenAI
        response = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            response_format=response_format,
            **openai_options,
        )
        
        # Konwertuj odpowiedź OpenAI na format kompatybilny z Ollama
        return {
            "message": {
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role,
            }
        }
    
    def is_available(self) -> bool:
        """Sprawdza czy OpenAI jest dostępne."""
        if not self.client:
            return False
        try:
            # Proste sprawdzenie - próba listowania modeli
            self.client.models.list()
            return True
        except Exception:
            return False


def get_ai_provider(use_cloud: bool = None) -> AIProvider:
    """
    Factory function do tworzenia odpowiedniego dostawcy AI.
    
    Args:
        use_cloud: True dla OpenAI, False dla Ollama (domyślnie z Config)
        
    Returns:
        Instancja AIProvider
    """
    if use_cloud is None:
        use_cloud = Config.USE_CLOUD_AI
    
    if use_cloud:
        return OpenAIProvider()
    else:
        return OllamaProvider()

