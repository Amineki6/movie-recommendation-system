# Use the official Python image from Docker Hub
FROM python:3.11-slim

# Install curl
RUN apt-get update && apt-get install -y curl && apt-get clean

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install CPU-only version of PyTorch
RUN pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# Expose the port Flask is running on
EXPOSE 7070

ENV PYTHONUNBUFFERED=1

# Define environment variable
ENV FLASK_APP=app.py

# Run the application
CMD ["python", "app.py"]

