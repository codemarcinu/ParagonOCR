import sys
import torch
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GPU-Verifier")

def check_gpu():
    logger.info("Checking GPU configuration...")
    
    # 1. Check CUDA availability
    if not torch.cuda.is_available():
        logger.error("❌ CUDA is NOT available to PyTorch.")
        return False
    
    device_name = torch.cuda.get_device_name(0)
    device_count = torch.cuda.device_count()
    current_device = torch.cuda.current_device()
    
    logger.info(f"✅ CUDA is available! Found {device_count} device(s).")
    logger.info(f"   Current Device: {current_device}")
    logger.info(f"   Device Name: {device_name}")
    
    # 2. Check EasyOCR (if installed)
    try:
        import easyocr
        logger.info("Checking EasyOCR...")
        # Try to initialize reader with GPU
        reader = easyocr.Reader(['en'], gpu=True, verbose=False)
        logger.info("✅ EasyOCR loaded successfully with gpu=True")
    except ImportError:
        logger.warning("⚠️ EasyOCR not installed (skip check).")
    except Exception as e:
        logger.error(f"❌ EasyOCR failed to initialize on GPU: {e}")
        return False

    return True

if __name__ == "__main__":
    success = check_gpu()
    if success:
        logger.info("Verification PASSED: System is ready for GPU acceleration.")
        sys.exit(0)
    else:
        logger.error("Verification FAILED: GPU issues detected.")
        sys.exit(1)
