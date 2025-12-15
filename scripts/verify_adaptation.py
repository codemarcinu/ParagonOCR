
import sys
import os
import requests
import torch
import easyocr

def check_gpu():
    print("--- GPU / EasyOCR Check ---")
    try:
        if torch.cuda.is_available():
            print(f"CUDA Available: Yes")
            print(f"Device Name: {torch.cuda.get_device_name(0)}")
        else:
            print("CUDA Available: NO")

        reader = easyocr.Reader(['pl'], gpu=True, download_enabled=False)
        print(f"EasyOCR Device: {reader.device}")
        if reader.device == 'cuda':
            print("SUCCESS: EasyOCR is using GPU.")
            return True
        else:
            print("WARNING: EasyOCR is NOT using GPU.")
            return False
    except Exception as e:
        print(f"Error checking GPU: {e}")
        return False

def check_ollama():
    print("\n--- Ollama Check ---")
    try:
        response = requests.get("http://localhost:11434")
        if response.status_code == 200:
            print("Ollama Server: Reachable")
        else:
            print(f"Ollama Server: Error {response.status_code}")
            return False
        
        # Check models
        resp = requests.get("http://localhost:11434/api/tags")
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json()['models']]
            print(f"Available Models: {models}")
            required = ["SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M", "llava:latest"]
            missing = [r for r in required if r not in models]
            if not missing:
                print("SUCCESS: All required models present.")
                return True
            else:
                print(f"WARNING: Missing models: {missing}")
                return False
    except Exception as e:
        print(f"Error checking Ollama: {e}")
        return False

if __name__ == "__main__":
    gpu_ok = check_gpu()
    ollama_ok = check_ollama()
    
    if gpu_ok and ollama_ok:
        print("\nOVERALL STATUS: GREEN")
        sys.exit(0)
    else:
        print("\nOVERALL STATUS: RED (See details above)")
        sys.exit(1)
