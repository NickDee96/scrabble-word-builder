import os

from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from typing import Optional

from scrabble_engine import scrabble_word_builder, word_count
from board_engine import generate_moves, BOARD_SIZE

# --- Configuration (environment-driven) ------------------------------------
_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

# Input limits guard against pathological requests: the search space grows very
# fast with rack size and the number of blank tiles.
MAX_RACK_TILES = int(os.getenv("MAX_RACK_TILES", "10"))
MAX_BLANKS = int(os.getenv("MAX_BLANKS", "2"))
MAX_BOARD_LETTERS = int(os.getenv("MAX_BOARD_LETTERS", "15"))
BLANK_CHARS = {" ", "?"}


def _find_words_rate_limit() -> str:
    """Rate limit for the find-words endpoint (read per request so it can be tuned)."""
    return os.getenv("RATE_LIMIT_FIND_WORDS", "30/minute")


def _analyze_rate_limit() -> str:
    """Rate limit for the board-analysis endpoint (heavier than find-words)."""
    return os.getenv("RATE_LIMIT_ANALYZE", "20/minute")


app = FastAPI(
    title="Scrabble Word Builder API",
    description="Find words for Scrabble from available letters",
)

# Rate limiting, keyed by client IP.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS restricted to known origins (no credentials, minimal methods/headers).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Set up templates for HTML rendering
templates = Jinja2Templates(directory="templates")


# --- Pydantic models -------------------------------------------------------
class FindWordsRequest(BaseModel):
    letters: str
    boardLetters: Optional[str] = ""


class WordResult(BaseModel):
    word: str
    score: int
    length: int


class FindWordsResponse(BaseModel):
    success: bool
    results: list[WordResult]
    total_words: int
    message: str


class HealthResponse(BaseModel):
    status: str
    message: str
    word_count: int


class BoardCell(BaseModel):
    letter: str
    blank: bool = False


class AnalyzeRequest(BaseModel):
    board: list[list[Optional[BoardCell]]]
    rack: str
    maxResults: int = 15
    mode: str = "equity"


class PlacedTileOut(BaseModel):
    row: int
    col: int
    letter: str
    blank: bool


class PlayOut(BaseModel):
    word: str
    row: int
    col: int
    direction: str
    score: int
    leave: str
    equity: float
    leaveValue: float
    tiles: list[PlacedTileOut]
    crossWords: list[str]


class AnalyzeResponse(BaseModel):
    plays: list[PlayOut]
    total: int
    message: str


def _validate_rack(letters: str, board_letters: str) -> None:
    """Validate and bound user input; raise HTTPException on any violation."""
    if not letters:
        raise HTTPException(status_code=400, detail="Letters are required")
    if not all(c.isalpha() or c in BLANK_CHARS for c in letters):
        raise HTTPException(
            status_code=400,
            detail="Letters must contain only alphabetic characters, spaces, or '?' for blanks",
        )
    if board_letters and not all(c.isalpha() for c in board_letters):
        raise HTTPException(
            status_code=400, detail="Board letters must contain only alphabetic characters"
        )

    n_blanks = sum(1 for c in letters if c in BLANK_CHARS)
    if len(letters) > MAX_RACK_TILES:
        raise HTTPException(status_code=422, detail=f"Too many tiles (max {MAX_RACK_TILES})")
    if n_blanks > MAX_BLANKS:
        raise HTTPException(status_code=422, detail=f"Too many blank tiles (max {MAX_BLANKS})")
    if len(board_letters) > MAX_BOARD_LETTERS:
        raise HTTPException(
            status_code=422, detail=f"Too many board letters (max {MAX_BOARD_LETTERS})"
        )


@app.post("/api/find-words", response_model=FindWordsResponse)
@limiter.limit(_find_words_rate_limit)
async def api_find_words(request: Request, request_data: FindWordsRequest):
    """Find every valid word playable from the supplied letters."""
    letters = request_data.letters.strip()
    board_letters = request_data.boardLetters.strip() if request_data.boardLetters else ""

    _validate_rack(letters, board_letters)

    try:
        words_scores = scrabble_word_builder(letters, board_letters)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error in api_find_words: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")

    results = [
        WordResult(word=word, score=score, length=len(word)) for word, score in words_scores
    ]
    results.sort(key=lambda r: (-r.score, r.word))

    return FindWordsResponse(
        success=True,
        results=results,
        total_words=len(results),
        message=f"Found {len(results)} words",
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
@limiter.limit(_analyze_rate_limit)
async def api_analyze(request: Request, data: AnalyzeRequest):
    """Analyze a full board position and return the best legal plays for a rack."""
    if len(data.board) != BOARD_SIZE or any(len(row) != BOARD_SIZE for row in data.board):
        raise HTTPException(status_code=422, detail=f"Board must be {BOARD_SIZE}x{BOARD_SIZE}")

    rack = data.rack.strip().upper()
    if not rack:
        raise HTTPException(status_code=400, detail="Rack is required")
    if len(rack) > 7:
        raise HTTPException(status_code=422, detail="Rack cannot exceed 7 tiles")
    if not all(c.isalpha() or c in BLANK_CHARS for c in rack):
        raise HTTPException(
            status_code=400, detail="Rack must contain only letters or '?' for blanks"
        )

    letters = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    blanks = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = data.board[r][c]
            if cell is None:
                continue
            value = cell.letter.strip().upper()
            if len(value) != 1 or not value.isalpha():
                raise HTTPException(status_code=422, detail=f"Invalid board letter at ({r}, {c})")
            letters[r][c] = value
            blanks[r][c] = cell.blank

    moves = generate_moves(letters, blanks, rack)
    limit = max(1, min(data.maxResults, 50))
    mode = data.mode if data.mode in ("equity", "score") else "equity"
    if mode == "equity":
        moves.sort(key=lambda m: (-m.equity, m.word))
    else:
        moves.sort(key=lambda m: (-m.score, m.word))

    # Recommendation list: keep the best placement of each distinct word (moves are
    # already sorted by the chosen metric) so the same word does not repeat.
    seen_words: set = set()
    unique = []
    for move in moves:
        if move.word in seen_words:
            continue
        seen_words.add(move.word)
        unique.append(move)

    plays = [
        PlayOut(
            word=m.word,
            row=m.row,
            col=m.col,
            direction=m.direction,
            score=m.score,
            leave=m.leave,
            equity=round(m.equity, 1),
            leaveValue=round(m.leave_value, 1),
            tiles=[
                PlacedTileOut(row=t.row, col=t.col, letter=t.letter, blank=t.is_blank)
                for t in m.tiles
            ],
            crossWords=m.cross_words,
        )
        for m in unique[:limit]
    ]
    return AnalyzeResponse(plays=plays, total=len(moves), message=f"Found {len(moves)} plays")


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify the API is running."""
    return HealthResponse(
        status="healthy",
        message="Scrabble Word Builder API is running",
        word_count=word_count(),
    )


@app.get("/", response_class=HTMLResponse)
async def scrabble_word_builder_web(request: Request):
    """Web interface for the Scrabble word builder."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
async def scrabble_word_builder_web_post(
    request: Request,
    letters: str = Form(...),
    board_letters: str = Form(default=""),
):
    """Handle form submission for the web interface."""
    letters = letters.strip()
    board_letters = board_letters.strip()
    _validate_rack(letters, board_letters)

    words_scores = scrabble_word_builder(letters, board_letters)
    words_by_length = {}
    for word, score in words_scores:
        words_by_length.setdefault(len(word), []).append((word, score))
    for length in words_by_length:
        words_by_length[length].sort(key=lambda x: x[0])  # alphabetical
        words_by_length[length].sort(key=lambda x: x[1], reverse=True)  # then score
    return templates.TemplateResponse(
        "result.html", {"request": request, "words_by_length": words_by_length}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
