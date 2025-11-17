#!/bin/bash
# Script to run the application locally

echo "Starting Flask API server on port 5001..."
python3 api.py &
API_PID=$!

echo "Waiting for API to start..."
sleep 3

echo "Starting frontend server on port 8000..."
cd public
python3 -m http.server 8000 &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "Application is running locally!"
echo "=========================================="
echo ""
echo "Frontend: http://localhost:8000"
echo "API: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
trap "kill $API_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

