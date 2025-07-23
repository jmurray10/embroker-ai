#!/bin/bash
set -e

echo "Starting Embroker Insurance Chatbot..."

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL..."
    while ! python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
"; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "PostgreSQL is up - executing command"
    
    # Initialize database
    echo "Initializing database..."
    python -c "
from src.app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created.')
"
fi

# Create necessary directories
mkdir -p logs attached_assets sessions

# Check if required environment variables are set
if [ -z "$POC_OPENAI_API" ]; then
    echo "ERROR: POC_OPENAI_API environment variable is required"
    exit 1
fi

if [ -z "$PINECONE_API_KEY" ]; then
    echo "WARNING: PINECONE_API_KEY not set - vector search will be limited"
fi

echo "Environment setup complete."

# Execute the main command
exec "$@"