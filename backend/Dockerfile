# Smart AI Interview Assistant: Backend Dockerfile

# Use full Python image for reliable apt/system deps
FROM python:3.10-bookworm

# Install system dependencies with retry logic and mirror selection for reliability
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      build-essential \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Work Directory
WORKDIR /app

# Copy Requirements first (Cache layer)
COPY requirements.txt .

# Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Install PyTorch (CPU version by default, GPU managed by driver mapping)
# CPU by default; for GPU, rebuild with: --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu121
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install torch torchvision --index-url $TORCH_INDEX

# Copy Application Code
COPY . .

# Expose Port 8000
EXPOSE 8000

# Run Application
CMD ["python", "run.py"]
