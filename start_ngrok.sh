#!/bin/bash
# Helper script to start ngrok for the backend

if [ ! -f "./ngrok" ]; then
    echo "ngrok not found in current directory. Downloading..."
    wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
    tar -xvzf ngrok-v3-stable-linux-amd64.tgz
    chmod +x ngrok
    rm ngrok-v3-stable-linux-amd64.tgz
fi

echo "Starting ngrok on port 5000..."
echo "Please copy the Forwarding URL (https://....ngrok-free.app) and update your .env file."
echo "Example: MPESA_STK_CALLBACK_URL=https://your-id.ngrok-free.app/api/mpesa/callback"
echo ""

./ngrok http 5000
