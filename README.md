Project structure: 

# OpenAlgo + Custom Trading Engine Setup

## Project Structure

```
engine-docker-setup/
├── .env                        # All configuration & secrets (do NOT commit!)
├── docker-compose.yaml         # Orchestrates both services
├── engine/                     # Your custom trading engine
│   ├── app.py                  # Flask server (start/stop/status)
│   ├── config.py               # Loads env vars safely
│   ├── openalgo_calls.py       # API wrappers for OpenAlgo
│   ├── data_fetcher.py         # Stock scanner + 5-min data loop
│   ├── trading_engine.py       # Position/PnL/risk management logic
│   ├── indicators.py           # RSI, MACD, BB, EMA, Stoch, ADX, ATR
│   ├── Dockerfile              # Builds trading-engine image
│   └── requirements.txt
└── openalgo/                   # Cloned or copied OpenAlgo project
    ├── Dockerfile              # Official multi-stage build
    └── ... (rest of OpenAlgo files)


```


Step 1 Installation & Setup 
```
mkdir engine-docker-setup
cd engine-docker-setup
```
Copy/clone projects  Copy your trading engine files (files in this repo) into engine/subfolder
Copy/clone OpenAlgo (https://github.com/marketcalls/openalgo.git) into openalgo/subfolder

Step 2 
Create .env file in root ( inside engine-docker-setup folder)
Add following 2 keys::
```
API_KEY='youropenalgoKey'
STRATEGY='YOURSTRATEGYNAME'
```
and then copy all the properties from .sample.env file from openalgo, and update the following properties ::
```
BROKER_API_KEY='<yourBrokerKey>'
BROKER_API_SECRET ='<yourSecretKey>'
FLASK_HOST_IP='0.0.0.0'
WEBSOCKET_HOST='0.0.0.0'
WEBSOCKET_URL='ws://localhost:8765'
ZMQ_HOST='0.0.0.0'
REDIRECT_URL = 'http://127.0.0.1:5000/<yourBrokerHere>/callback'
APP_KEY='<yourOlgoKey>'
```

Step 3 Create docker-compose.yaml file inside engine-docker-setup folder & copy the contents for it from the repo's docker-compose.yaml file

Step 4 
Open WSL from start menu and run the following command
```
cd /mnt/c/Users/chirag/engine-docker-setup
docker compose build
```
2 images would be build
<img width="837" height="235" alt="image" src="https://github.com/user-attachments/assets/0364cdb2-3757-4970-98f9-3cd3d2156d75" />

```
docker compose up
```
you will be able to see below logs for both the applications,
<img width="1888" height="179" alt="image" src="https://github.com/user-attachments/assets/3a55649b-fec8-4029-94af-0482f0965748" />
<img width="1119" height="419" alt="image" src="https://github.com/user-attachments/assets/26a8140e-0247-415f-9a7b-4a20bcfe4aca" />

you can now access openalgo via UI at http://127.0.0.1:5000/

Hit the engine on below endpoint and you are good to go 
<img width="770" height="367" alt="image" src="https://github.com/user-attachments/assets/6e795a25-78e7-462a-b1bd-86fde85aa01e" />
