# 🏗️ Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (gcc and others)
RUN apt update && \
    apt install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependencies and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 🏗️ Stage 2: Final lightweight runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary runtime dependencies from builder stage
COPY --from=builder /install /usr/local
COPY . .

EXPOSE 5000
CMD ["python", "coffee_roaster_web.py"]
