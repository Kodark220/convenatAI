#!/bin/bash
# convenatAI — startup script
# Sets up genlayer CLI account and starts the FastAPI backend

set -e

echo "=== convenatAI startup ==="

# Import GenLayer account if GENLAYER_PRIVATE_KEY is set
if [ -n "$GENLAYER_PRIVATE_KEY" ] && [ -n "$GENLAYER_PASSWORD" ]; then
    # Check if account already exists
    if ! genlayer account list 2>/dev/null | grep -q "convenatAI"; then
        echo "Importing GenLayer account..."
        # Remove 0x prefix if present
        PK="${GENLAYER_PRIVATE_KEY#0x}"
        echo "$PK" | genlayer account import \
            --name convenatAI \
            --private-key "$PK" \
            --password "$GENLAYER_PASSWORD" 2>&1
        echo "Account imported."
    else
        echo "GenLayer account already exists."
    fi

    # Set network
    echo "Setting GenLayer network to ${GENLAYER_NETWORK:-studionet}..."
    echo "$GENLAYER_PASSWORD" | genlayer network set "${GENLAYER_NETWORK:-studionet}" 2>/dev/null || true
fi

echo "Starting convenatAI API server..."
# Start the uvicorn server
exec uvicorn serve:app --host 0.0.0.0 --port "${PORT:-8080}"
