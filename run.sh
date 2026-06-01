#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}⚽ Starting Football Analytics Platform...${NC}\n"

# 1. Start the Backend
echo -e "${BLUE}▶ Starting FastAPI Backend...${NC}"
cd backend
# Make sure we're using python3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi
$PYTHON_CMD -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a brief moment for the backend to initialize
sleep 2

# 2. Start the Frontend
echo -e "\n${BLUE}▶ Starting React Frontend...${NC}"
cd frontend
# Check if node_modules exists, if not run npm install
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}✅ Both servers are running!${NC}"
echo -e "👉 Frontend: http://localhost:3000"
echo -e "👉 Backend:  http://localhost:8000"
echo -e "\n${RED}Press Ctrl+C to stop both servers.${NC}\n"

# Trap SIGINT (Ctrl+C) and SIGTERM to kill background processes cleanly
trap "echo -e '\n${BLUE}🛑 Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Wait for background processes to keep the script running
wait
