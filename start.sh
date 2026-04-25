#!/bin/bash
# start.sh -- Launch PrivacyLens (FastAPI backend + React frontend)

echo "Starting PrivacyLens..."

# Start FastAPI backend
echo "Starting API server on port 8000..."
python api/start.py &
API_PID=$!

# Wait briefly for API to be ready
sleep 2

# Start React frontend
echo "Starting React app on port 5173..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "╔════════════════════════════════════╗"
echo "║  PrivacyLens is running!           ║"
echo "║                                    ║"
echo "║  App:  http://localhost:5173       ║"
echo "║  API:  http://localhost:8000       ║"
echo "║  Docs: http://localhost:8000/docs  ║"
echo "╚════════════════════════════════════╝"

# Wait for both processes
wait $API_PID $FRONTEND_PID
