@echo off
REM PostOptima — One-command setup and run
echo ========================================
echo   PostOptima — Setup and Run
echo ========================================

echo.
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [2/4] Running tests...
pytest tests/ -v --tb=short

echo.
echo [3/4] Running optimizer pipeline...
python main.py --data-dir data/raw --output results/recommendations.json

echo.
echo [4/4] Starting API server...
echo   Frontend: cd frontend ^&^& npm install ^&^& npm run dev
echo   API will be available at http://localhost:8000
python api.py
