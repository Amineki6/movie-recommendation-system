# Use the official Python image from Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt first for better caching
COPY requirements.txt /app/

# Copy the rest of the application code
COPY . /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask is running on
EXPOSE 3040

# Define environment variable
ENV FLASK_APP=app.py

# Run the application
CMD ["python", "app.py"]

