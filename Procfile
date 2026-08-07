release: playwright install --with-deps chromium
worker: python bot.py
web: uvicorn api:app --host 0.0.0.0 --port $PORT
