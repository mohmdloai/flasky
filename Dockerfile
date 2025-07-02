# Use official Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Copy .env file if exists
COPY .env .env
# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose the port Flask will run on
EXPOSE 3000

# Set default command
CMD ["python", "app.py"]
