# Trading Bot API

FastAPI backend for Trading Bot event streaming to Supabase.

## Features

- **POST /api/decisions**: Publish decision events
- **POST /api/positions**: Update position status
- **POST /api/readiness**: Store readiness snapshots
- **POST /api/errors**: Log execution errors
- **POST /api/status**: Update bot status
- **GET /api/decisions**: Fetch latest decisions
- **GET /api/positions**: Fetch open positions
- **GET /api/readiness/{contract}**: Get readiness for contract
- **GET /api/status**: Get latest bot status

## Setup

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

3. Run locally:
```bash
python main.py
# or
uvicorn main:app --reload
```

4. API will be available at: `http://localhost:8000`
5. Docs available at: `http://localhost:8000/docs`

### Docker

Build and run:
```bash
docker build -t trading-bot-api .
docker run -p 8000:8000 --env-file .env trading-bot-api
```

### Cloud Deployment

Deploy to Google Cloud Run:
```bash
gcloud run deploy trading-bot-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SUPABASE_URL=xxx,SUPABASE_KEY=xxx
```

Or Railway:
```bash
# Connect repo to Railway, set env vars in dashboard
# Auto-deploy on git push
```

## Integration with Bot

The bot uses `SupabasePublisher` to post events to this API:

```python
from trading_bot.integrations.supabase_publisher import SupabasePublisher

publisher = SupabasePublisher(api_url="http://localhost:8000")

# Publish decision
await publisher.publish_decision(decision_event)

# Publish position
await publisher.publish_position(position_update)
```

## Supabase Realtime

Once events are inserted into Supabase tables, the UI can subscribe to real-time changes:

```typescript
const supabase = createClient(url, key);

supabase
  .channel('decisions')
  .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'decisions' }, (payload) => {
    console.log('New decision:', payload.new);
  })
  .subscribe();
```

## API Docs

Interactive API documentation: `http://localhost:8000/docs`

OpenAPI schema: `http://localhost:8000/openapi.json`
