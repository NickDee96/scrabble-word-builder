from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import itertools
from typing import Optional

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

# load a text file containing a list of english words
with open('Collins Scrabble Words (2019).txt', 'r') as f:
    english_words = set(f.read().splitlines())

# Scrabble letter scores
scores = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8,
    'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1,
    'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

def word_score(word, zero_indices=[]):
    """
    Calculate the score of a word based on Scrabble letter scores.
    """
    return sum(scores.get(letter.upper(), 0) if i not in zero_indices else 0 for i, letter in enumerate(word))

def scrabble_word_builder(letters, board_letters):
    """
    Generate all possible words that can be formed from the given letters and board letters.
    """
    letters = [x.upper() for x in letters]
    board_letters = ''.join([x.upper() for x in board_letters])
    possible_words = []
    for i in range(1, len(letters) + 1):
        for subset in itertools.permutations(letters, i):
            subset = list(subset)  # Convert tuple to list
            # If a blank space is encountered, replace it with each possible letter
            if ' ' in subset:
                for replacement in scores.keys():
                    subset_replaced = [letter if letter != ' ' else replacement for letter in subset]
                    zero_indices = [i for i, letter in enumerate(subset_replaced) if letter == replacement]
                    # Insert the board letters at all possible positions
                    for j in range(len(subset_replaced) + 1):
                        word = ''.join(subset_replaced[:j] + list(board_letters) + subset_replaced[j:])
                        if word in english_words:
                            possible_words.append((word, word_score(word, zero_indices)))
            else:
                # Insert the board letters at all possible positions
                for j in range(len(subset) + 1):
                    word = ''.join(subset[:j] + list(board_letters) + subset[j:])
                    if word in english_words:
                        possible_words.append((word, word_score(word)))
    possible_words = list(set(possible_words))        
    # Sort words by score
    possible_words.sort(key=lambda x: x[1], reverse=False)
    return possible_words

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
        word_count=len(english_words)
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