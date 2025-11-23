"""
Abstrakcje dla dostawców AI (LLM).

Wspiera:
- OpenAI (Cloud) - jedyny obsługiwany dostawca w wersji webowej
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import mimetypes
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
                    
                    # Określ typ MIME na podstawie rozszerzenia pliku
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if not mime_type or not mime_type.startswith('image/'):
                        # Fallback: sprawdź rozszerzenie ręcznie
                        img_path_lower = img_path.lower()
                        if img_path_lower.endswith('.png'):
                            mime_type = 'image/png'
                        elif img_path_lower.endswith(('.jpg', '.jpeg')):
                            mime_type = 'image/jpeg'
                        else:
                            # Domyślnie JPEG jeśli nie można określić
                            mime_type = 'image/jpeg'
                    
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{img_data}"}
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
    
    W wersji webowej zawsze zwraca OpenAIProvider (Ollama nie jest obsługiwane).
    
    Args:
        use_cloud: Ignorowane - zawsze używa OpenAI w wersji webowej
        
    Returns:
        Instancja OpenAIProvider
    """
    # W wersji webowej zawsze używamy OpenAI
    return OpenAIProvider()

