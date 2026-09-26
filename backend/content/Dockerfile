# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set PYTHONPATH to allow relative imports
ENV PYTHONPATH="/app:${PYTHONPATH}"

# # Expose port
# EXPOSE 8000

# # Run the application via entrypoint script
# ENTRYPOINT ["./docker-entrypoint.sh"]