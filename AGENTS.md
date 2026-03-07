# Spotify X-Ray - Project Documentation

## Project Overview

Spotify X-Ray is a web application that enhances the Spotify listening experience by providing AI-powered insights about currently playing songs. It displays the artist's intent, song meaning, and interesting facts about the track using Google's Gemini AI model with real-time web search capabilities.

### Key Features
- Spotify OAuth authentication
- Real-time currently playing track monitoring
- AI-generated song analysis (meaning and facts)
- Redis-based caching for song information
- Server-Sent Events (SSE) for live updates
- Responsive web interface

## Technology Stack

### Backend
- **Python 3.13** with Alpine Linux 3.22 (Docker base image)
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **Redis** - Session storage and caching
- **LangChain + Google GenAI** - AI/LLM integration

### Frontend
- Vanilla HTML5, CSS3, JavaScript
- Server-Sent Events (SSE) for real-time updates
- Google Fonts (Be Vietnam Pro)

### External APIs
- **Spotify Web API** - User authentication and currently playing track
- **Google Gemini API** - AI-powered song analysis with Google Search grounding

## Project Structure

```
spotify-xray/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and environment variables
│   ├── spotify.py           # Spotify API integration
│   ├── xray.py              # AI song analysis using Gemini
│   ├── utils.py             # Utility functions
│   ├── exceptions.py        # Custom exception classes
│   ├── requirements.txt     # Python dependencies
│   └── static/              # Frontend assets
│       ├── index.html       # Main application page
│       ├── login.html       # Spotify login page
│       ├── main.js          # Frontend JavaScript
│       ├── styles.css       # Styling
│       └── assets/          # Images
├── k8s/manifests/           # Kubernetes deployment manifests
├── Dockerfile               # Container build instructions
├── compose.yaml             # Docker Compose configuration
├── docker-bake.hcl          # Docker Buildx bake configuration
├── .env.example             # Environment variables template
└── .gitignore               # Git ignore rules
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

| Variable | Description |
|----------|-------------|
| `CLIENT_ID` | Spotify App Client ID from Spotify Developer Dashboard |
| `CLIENT_SECRET` | Spotify App Client Secret |
| `REDIRECT_URI` | OAuth callback URL (e.g., `http://127.0.0.1:5173/callback`) |
| `SESSION_SECRET_KEY` | Secret key for session management |
| `REDIS_HOST` | Redis hostname (`redis` for Docker, `localhost` for local) |
| `REDIS_PORT` | Redis port (default: 6379) |
| `REDIS_PASSWORD` | Redis authentication password |
| `GOOGLE_API_KEY` | Google API key for Gemini access |

### Spotify App Setup
1. Create an app at https://developer.spotify.com/dashboard
2. Add `http://127.0.0.1:5173/callback` (or your redirect URI) to Redirect URIs
3. Copy Client ID and Client Secret to `.env`

## Build and Run Commands

### Local Development (without Docker)

```bash
cd src
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 80 --reload
```

### Docker Compose (Recommended for local)

```bash
# Start the application and Redis
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Docker Buildx (Multi-platform)

```bash
docker buildx bake
```

### Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace spotify-xray

# Apply secrets (create from 04-backend-secrets.yaml.example first)
kubectl apply -f k8s/manifests/04-backend-secrets.yaml

# Apply manifests
kubectl apply -f k8s/manifests/
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/livez` | GET | Health check endpoint, returns uptime |
| `/authorize` | GET | Initiates Spotify OAuth flow |
| `/callback` | GET | OAuth callback handler |
| `/refresh_token` | GET | Refresh Spotify access token |
| `/xray` | GET | SSE endpoint for real-time song info and AI analysis |
| `/current_user_id` | GET | Get current Spotify user ID |
| `/` | GET | Serves static frontend files |

## Code Organization

### Main Modules

- **main.py**: FastAPI app setup, route handlers, Redis client initialization
- **spotify.py**: OAuth flow, token management, Spotify API calls
- **xray.py**: Gemini AI integration, song analysis, caching logic
- **utils.py**: Helper functions for song data extraction, smart polling
- **config.py**: Environment configuration loading
- **exceptions.py**: Custom exception classes

### Authentication Flow

1. User visits `/` → redirected to `/authorize` if no session
2. `/authorize` generates state token, redirects to Spotify OAuth
3. Spotify redirects to `/callback` with authorization code
4. Tokens stored in Redis with session ID cookie
5. Session ID used for subsequent API calls

### Caching Strategy

- **Access tokens**: Stored for 60 minutes
- **Refresh tokens**: Stored for 30 days
- **Song analysis**: Cached for 24 hours (86400 seconds) using song ID as key
- **OAuth state**: Valid for 5 minutes

## Development Conventions

### Code Style
- Type hints used throughout (`typing` module)
- f-strings for string formatting
- Logging with appropriate levels (INFO, DEBUG, ERROR, WARNING)
- Exception handling with custom exception classes

### Error Handling
- Custom exceptions: `StateMismatchException`, `InternalServerError`, `ExpiredTokenException`
- Graceful degradation with try-except blocks
- SSE error events for frontend communication

### Smart Polling
The `/xray` endpoint uses intelligent polling:
- Default poll interval: 5 seconds
- When song is playing: polls every 10% of remaining song duration
- Minimum poll interval: 5 seconds

## Security Considerations

1. **CSRF Protection**: OAuth state parameter verified against Redis
2. **Token Storage**: Spotify tokens stored server-side in Redis, not client-side
3. **Session Management**: Session ID in HTTP-only cookie
4. **Secrets Management**: Environment variables for all sensitive data
5. **Redis Authentication**: Password-protected Redis instance

## Testing

No automated test suite is currently configured. For manual testing:

1. Start the application with Docker Compose
2. Visit `http://localhost` in browser
3. Authenticate with Spotify
4. Play a song on Spotify
5. Verify real-time updates in the web interface

## Deployment Notes

### Docker Image
- Multi-architecture support: `linux/amd64`, `linux/arm64`
- Published to: `271122/spotify-xray:latest`
- Uses BuildKit cache mount for pip dependencies

### Kubernetes
- Namespace: `spotify-xray`
- Single replica deployment
- Ingress configured for nginx ingress controller
- Secrets must be base64 encoded before applying

## Known Limitations

1. No automated tests
2. No rate limiting on endpoints
3. Single user session per browser (no multi-user support)
4. Redis data is not persisted (ephemeral storage)
