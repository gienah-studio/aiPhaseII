#!/bin/bash

echo "Starting rebuild process..."

echo "Step 1/3: Stopping containers..."
docker-compose down
if [ $? -ne 0 ]; then
    echo "Error stopping containers"
    exit 1
fi

echo "Step 2/3: Rebuilding images..."
docker-compose build --no-cache
if [ $? -ne 0 ]; then
    echo "Error rebuilding images"
    exit 1
fi

echo "Step 3/3: Starting containers..."
docker-compose up
if [ $? -ne 0 ]; then
    echo "Error starting containers"
    exit 1
fi
