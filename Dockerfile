FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install dependencies
RUN pip install flask pandas numpy requests

# Copy all Python files
COPY . .

# Expose port for Flask
EXPOSE 5001

# Run the Flask app
CMD ["python", "app.py"]