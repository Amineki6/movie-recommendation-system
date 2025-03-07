# Use the official Python image from Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask is running on
EXPOSE 6090

# Define environment variable
ENV FLASK_APP=app.py

# Run the application
CMD ["python", "app.py"]

