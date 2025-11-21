# Use the official Microsoft Playwright image
FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Install the package in editable mode
RUN pip install -e .

# Install Playwright browsers (ensure they're available)
RUN playwright install chromium

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Use entrypoint to ensure package is installed and run scheduled collector
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
