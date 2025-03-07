#!/usr/bin/env bash
set -e  # Exit on error

# Start the Flask service in the background:
python /app/app.py &

# Wait for Flask to be ready
RETRIES=15
DELAY=5
URL="http://localhost:7070/train"

echo "Waiting for Flask to be ready..."

# Loop until the server responds or retries are exhausted
until curl -X POST -H "Content-Type: application/json" -d '{"train_cb": true, "train_cbf": false}' "$URL" || [ $RETRIES -eq 0 ]; do
    echo "Flask not ready yet... retrying in $DELAY seconds..."
    sleep $DELAY
    ((RETRIES--))
done

if [ $RETRIES -eq 0 ]; then
    echo "Failed to connect to Flask after multiple attempts."
    exit 1
else
    echo "Successfully triggered training!"
fi

# Keep the container running by waiting on the Flask process:
wait
