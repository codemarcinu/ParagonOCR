#!/bin/bash
# ParagonOCR Web Edition - Development server startup script
# Starts both backend and frontend development servers

set -e

echo "🚀 Starting ParagonOCR Web Edition development servers..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "${YELLOW}⚠️  Ollama doesn't seem to be running${NC}"
    echo "   Start it with: ${BLUE}ollama serve${NC}"
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "🔧 Starting backend server..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "${GREEN}✅ Servers started!${NC}"
echo ""
echo "Backend PID: ${BACKEND_PID}"
echo "Frontend PID: ${FRONTEND_PID}"
echo ""
echo "Access:"
echo "  Frontend: ${GREEN}http://localhost:5173${NC}"
echo "  Backend:  ${GREEN}http://localhost:8000${NC}"
echo "  API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "Logs:"
echo "  Backend:  ${BLUE}tail -f backend.log${NC}"
echo "  Frontend: ${BLUE}tail -f frontend.log${NC}"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for processes
wait

