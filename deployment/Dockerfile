FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY deployment/requirements.txt deployment/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r deployment/requirements.txt

# Install Playwright browsers (this will install system dependencies automatically)
RUN playwright install firefox

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]