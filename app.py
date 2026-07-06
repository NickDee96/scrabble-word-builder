from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from scrabble_engine import scrabble_word_builder, word_count

app = FastAPI(title="Scrabble Word Builder API", description="Find words for Scrabble from available letters")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates for HTML rendering
templates = Jinja2Templates(directory="templates")

# Pydantic models for request validation
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


@app.post("/api/find-words", response_model=FindWordsResponse)
async def api_find_words(request_data: FindWordsRequest):
    """
    API endpoint to find words from letters
    """
    try:
        letters = request_data.letters.strip()
        board_letters = request_data.boardLetters.strip() if request_data.boardLetters else ""
        
        if not letters:
            raise HTTPException(status_code=400, detail="Letters are required")
        
        # Validate letters contain only alphabetic characters and spaces
        if not all(c.isalpha() or c.isspace() for c in letters):
            raise HTTPException(status_code=400, detail="Letters must contain only alphabetic characters and spaces")
        
        if board_letters and not all(c.isalpha() or c.isspace() for c in board_letters):
            raise HTTPException(status_code=400, detail="Board letters must contain only alphabetic characters and spaces")
        
        words_scores = scrabble_word_builder(letters, board_letters)
        
        # Format the response for the frontend
        results = []
        for word, score in words_scores:
            results.append(WordResult(
                word=word,
                score=score,
                length=len(word)
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        return FindWordsResponse(
            success=True,
            results=results,
            total_words=len(results),
            message=f"Found {len(results)} words"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in api_find_words: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify the API is running
    """
    return HealthResponse(
        status="healthy",
        message="Scrabble Word Builder API is running",
        word_count=word_count(),
    )

@app.get("/", response_class=HTMLResponse)
async def scrabble_word_builder_web(request: Request):
    """
    Web interface for the Scrabble word builder
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def scrabble_word_builder_web_post(
    request: Request,
    letters: str = Form(...),
    board_letters: str = Form(default="")
):
    """
    Handle form submission for web interface
    """
    words_scores = scrabble_word_builder(letters, board_letters)
    words_by_length = {}
    for word, score in words_scores:
        if len(word) not in words_by_length:
            words_by_length[len(word)] = [(word, score)]
        else:
            words_by_length[len(word)].append((word, score))
    for length in words_by_length:
        words_by_length[length].sort(key=lambda x: x[0])  # Sort alphabetically
        words_by_length[length].sort(key=lambda x: x[1], reverse=True)  # Sort by score
    return templates.TemplateResponse("result.html", {
        "request": request,
        "words_by_length": words_by_length
    })

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000, reload=True)