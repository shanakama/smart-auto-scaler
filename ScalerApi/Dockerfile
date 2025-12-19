# Multi-stage build for DQN Kubernetes Resource Scaler
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt


# Final stage
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app.py .
COPY dqn_model_wrapper.py .
COPY core_functions.py .
COPY api_routes.py .
COPY k8s_client.py .
COPY scaling_service.py .
COPY config.yaml .

# Create directories and copy DQN agent from final-models
RUN mkdir -p /app/final-models /root/.kube
COPY ./final-models/dqn_agent.py /app/final-models/dqn_agent.py
COPY ./final-models/dqn_model.pt /app/final-models/dqn_model.pt

# Set Python path
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# Run application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
