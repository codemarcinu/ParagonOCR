# Use Python 3.10 slim as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# tesseract-ocr: The OCR engine
# tesseract-ocr-pol: Polish language data
# poppler-utils: For PDF processing
# libgl1, libglib2.0-0: Required by OpenCV (cv2)
# curl: For healthchecks
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-pol \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
# Copy requirements first to leverage cache
COPY backend/requirements.txt .

# Install dependencies
# Note: For strict CUDA usage with Torch, one might use --extra-index-url https://download.pytorch.org/whl/cu118
# But usually the default torch wheel includes CPU support, and CUDA is larger. 
# We'll stick to standard installation, assuming requirements.txt handles versions.
# If explicit CUDA torch is needed, the user might need to adjust requirements.
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Expose port
EXPOSE 8000

# Run command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
