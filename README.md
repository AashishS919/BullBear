### Frontend 

Requires Node.js 18+ and npm.

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
```

Build for production:

```bash
npm run build
npm run preview
```

### Backend 

Requires Python 3.11+ (3.14 works; pinned deps ship 3.14 wheels).

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
# source venv/bin/activate         # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

Run the backend tests:

```powershell
cd backend
pytest app/tests -q
```

### Database + ML 

```powershell
# 1) Seed MongoDB (backend venv) - creates the 'bullbear' DB + 5-year market_candles
cd backend
venv\Scripts\python.exe scripts\seed_mongo.py

# 2) Train the LSTM + publish predictions (separate Python 3.12 ML venv)
cd ..\ml
C:\Python312\python.exe -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe train.py
venv\Scripts\python.exe infer.py
venv\Scripts\python.exe backtest.py   # predicted-vs-actual series for the Charts page

# 3) Run the API against Mongo (backend/.env: BB_DATA_BACKEND=mongo)
cd ..\backend
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Refreshing market data to the latest session
```powershell
cd backend
venv\Scripts\python.exe scripts\fetch_sharesansar.py                     
venv\Scripts\python.exe scripts\data_pipeline.py --source sharesansar     

cd ..\ml
venv\Scripts\python.exe infer.py                                        
venv\Scripts\python.exe backtest.py                                     




