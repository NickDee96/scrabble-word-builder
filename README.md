# Scrabble Word Builder

A full-stack web application that generates all possible words from given letters, designed as a solver for Scrabble and other word games. Features a modern React frontend with a FastAPI backend.

## 🎯 Features

- **Modern Web Interface**: Beautiful, responsive React/Next.js frontend
- **Fast Word Generation**: Efficient FastAPI backend with comprehensive word database
- **Interactive Scrabble Board**: Visual board interface for strategic planning
- **Advanced Filtering**: Filter by word length, score, and patterns
- **Real-time Results**: Instant word generation as you type
- **Mobile Responsive**: Works seamlessly on all devices

## 🏗️ Architecture

```
Frontend (Next.js/React)  ←→  Backend (FastAPI/Python)
     Port 3000                    Port 5000
     
┌─────────────────┐         ┌─────────────────┐
│  Modern UI      │   HTTP  │  Word Engine    │
│  - React/Next   │  ←────→ │  - FastAPI API  │
│  - Tailwind CSS │   API   │  - Word DB      │
│  - TypeScript   │         │  - Algorithms   │
└─────────────────┘         └─────────────────┘
```

## 📁 Project Structure

```
scrabble/
├── app.py                          # FastAPI backend server
├── scrabble.py                     # Command-line version
├── ui.py                          # Tkinter GUI (legacy)
├── start-services.bat             # Easy startup script
├── test-connection.html           # Integration test page
├── Collins Scrabble Words (2019).txt  # Word database
├── requirements.txt               # Python dependencies
└── frontend/                      # Next.js frontend
    ├── app/
    │   ├── page.tsx              # Main application page
    │   ├── layout.tsx            # App layout
    │   └── globals.css           # Global styles
    ├── components/
    │   ├── scrabble-board.tsx    # Interactive board
    │   └── ui/                   # Reusable UI components
    ├── package.json              # Node dependencies
    └── .env.local               # Environment configuration
```

## 🚀 Quick Start

### Option 1: Docker (Recommended)

The easiest way to run the application is using Docker:

```bash
# Clone and navigate to the project
cd scrabble

# Start with Docker Compose (Production)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Or use the helper script (Windows)
docker-helper.bat start prod

# Or use the helper script (Linux/Mac)
./docker-helper.sh start prod
```

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

For detailed Docker setup instructions, see [DOCKER_SETUP.md](DOCKER_SETUP.md).

### Option 2: Manual Setup

### Prerequisites
- Python 3.9+ with pip
- Node.js 16+ with npm
- Windows (for the batch script, or adapt for other OS)

### Option 1: Easy Setup (Windows)
1. Clone the repository
2. Double-click `start-services.bat`
3. Wait for both services to start
4. Open http://localhost:3000 in your browser

### Option 2: Manual Setup

#### 1. Setup Backend (FastAPI)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server (Uvicorn)
python app.py
```
The backend will run on http://localhost:5000

#### 2. Setup Frontend (Next.js)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
The frontend will run on http://localhost:3000

#### 3. Test Integration
Open `test-connection.html` in a browser to verify both services are running correctly.

## ⚙️ Configuration

All configuration is environment-driven; every value has a sensible default, so the app
runs with no setup. See [`.env.example`](.env.example) for a copy-paste template.

### Backend (FastAPI)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment label (informational) |
| `PORT` | `5000` | Port Uvicorn listens on |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated CORS allowlist |
| `MAX_RACK_TILES` | `10` | Max tiles (letters + blanks) per request |
| `MAX_BLANKS` | `2` | Max blank tiles per request |
| `MAX_BOARD_LETTERS` | `15` | Max board letters per request |
| `RATE_LIMIT_FIND_WORDS` | `30/minute` | Rate limit for `/api/find-words` |

### Frontend (Next.js)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5000` | Backend base URL the Next.js server proxies `/api/*` to |

Set the frontend value in `frontend/.env.local`.

## 🔧 API Endpoints

### Backend API (FastAPI - Port 5000)

#### `POST /api/find-words`
Find all possible words from given letters.

**Request:**
```json
{
  "letters": "WERTASH",
  "boardLetters": "BAK"
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "word": "WASHBOARD",
      "score": 15,
      "length": 9
    }
  ],
  "total_words": 42,
  "message": "Found 42 words"
}
```

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "message": "Scrabble Word Builder API is running",
  "word_count": 279496
}
```

## 🎮 Usage

### Web Application
1. Open http://localhost:3000
2. Enter your available letters in the "Your Letters" field
3. Optionally add board letters that are already placed
4. Click "Find Words" to generate all possible words
5. View results organized by length and sorted by score
6. Use the Interactive Board tab for visual game planning

### Command Line
```bash
python scrabble.py --letters "WERTASH" --board_letters "BAK"
```

### Programmatic Usage
```python
from scrabble import scrabble_word_builder

words = scrabble_word_builder(['W','E','R','T','A','S','H'], ['B','A','K'])
for word, score in words:
    print(f"{word}: {score} points")
```

## 🔄 Integration Details

The frontend and backend communicate via HTTP REST API:

1. **Frontend** (React/Next.js) makes HTTP requests to backend
2. **Backend** (Flask) processes word generation and returns JSON
3. **CORS** is enabled for cross-origin requests
4. **Error handling** provides user-friendly messages
5. **Loading states** show progress during API calls

### Key Integration Features:
- Environment-based API URL configuration
- Automatic retry logic for failed requests
- Real-time search with debouncing
- Responsive loading indicators
- Comprehensive error handling

## 🧠 Algorithm

The core engine (`scrabble_engine.py`) uses an **anagram signature index** for fast
lookups. At startup, every dictionary word is grouped by its *signature* — the sorted
tuple of its letters (e.g. `WREATHS` and `THAWERS` share `AEHRSTW`). Finding words then
works as follows:

1. Enumerate the distinct letter multisets reachable from the rack, expanding blank
   tiles (`?` or space) into wildcards.
2. Look up each multiset's signature in the index in O(1).
3. Keep words where any board letters appear as a contiguous block.
4. Score each word (blank tiles score 0) and return the best score per word, sorted.

This replaces the previous O(n!) permutation scan, returning results for a full
7-letter rack in a few milliseconds.

## 🎯 Future Enhancements

- **Performance Optimization**: ✅ Anagram signature index implemented (`scrabble_engine.py`)
- **Advanced Features**: 
  - Premium square multipliers
  - Word validation against game rules
  - Save/load game states
  - Multi-player support
- **Mobile App**: React Native implementation
- **AI Integration**: Suggest optimal moves
- **Statistics**: Track performance and improvement

## 👨‍💻 Author

**Nick Mumero** - Machine Learning Engineer
- GitHub: [@NickDee96](https://github.com/NickDee96)

## 📄 License

This project is open source and available under the MIT License.