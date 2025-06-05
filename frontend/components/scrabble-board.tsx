"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Trash2, Sparkles } from "lucide-react"

type SquareType = "normal" | "double-letter" | "triple-letter" | "double-word" | "triple-word" | "center"

interface BoardSquare {
  type: SquareType
  letter: string
  isPlaced: boolean
  isPermanent: boolean
}

interface ScrabbleBoardProps {
  onBoardChange?: (board: BoardSquare[][]) => void
  availableLetters: string
}

const BOARD_SIZE = 15

// Define the premium square layout for a standard Scrabble board
const getPremiumSquareType = (row: number, col: number): SquareType => {
  // Center square
  if (row === 7 && col === 7) return "center"

  // Triple Word Score squares
  const tripleWordSquares = [
    [0, 0],
    [0, 7],
    [0, 14],
    [7, 0],
    [7, 14],
    [14, 0],
    [14, 7],
    [14, 14],
  ]
  if (tripleWordSquares.some(([r, c]) => r === row && c === col)) return "triple-word"

  // Double Word Score squares
  const doubleWordSquares = [
    [1, 1],
    [1, 13],
    [2, 2],
    [2, 12],
    [3, 3],
    [3, 11],
    [4, 4],
    [4, 10],
    [10, 4],
    [10, 10],
    [11, 3],
    [11, 11],
    [12, 2],
    [12, 12],
    [13, 1],
    [13, 13],
  ]
  if (doubleWordSquares.some(([r, c]) => r === row && c === col)) return "double-word"

  // Triple Letter Score squares
  const tripleLetterSquares = [
    [1, 5],
    [1, 9],
    [5, 1],
    [5, 5],
    [5, 9],
    [5, 13],
    [9, 1],
    [9, 5],
    [9, 9],
    [9, 13],
    [13, 5],
    [13, 9],
  ]
  if (tripleLetterSquares.some(([r, c]) => r === row && c === col)) return "triple-letter"

  // Double Letter Score squares
  const doubleLetterSquares = [
    [0, 3],
    [0, 11],
    [2, 6],
    [2, 8],
    [3, 0],
    [3, 7],
    [3, 14],
    [6, 2],
    [6, 6],
    [6, 8],
    [6, 12],
    [7, 3],
    [7, 11],
    [8, 2],
    [8, 6],
    [8, 8],
    [8, 12],
    [11, 0],
    [11, 7],
    [11, 14],
    [12, 6],
    [12, 8],
    [14, 3],
    [14, 11],
  ]
  if (doubleLetterSquares.some(([r, c]) => r === row && c === col)) return "double-letter"

  return "normal"
}

const getSquareStyles = (type: SquareType, hasLetter: boolean) => {
  const baseStyles =
    "w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 border border-gray-300 flex items-center justify-center text-xs sm:text-sm font-bold cursor-pointer transition-all duration-200 hover:scale-105"

  if (hasLetter) {
    return `${baseStyles} bg-yellow-100 border-yellow-400 text-gray-800 shadow-md`
  }

  switch (type) {
    case "center":
      return `${baseStyles} bg-gradient-to-br from-pink-400 to-red-500 text-white shadow-lg`
    case "triple-word":
      return `${baseStyles} bg-gradient-to-br from-red-500 to-red-600 text-white`
    case "double-word":
      return `${baseStyles} bg-gradient-to-br from-pink-400 to-pink-500 text-white`
    case "triple-letter":
      return `${baseStyles} bg-gradient-to-br from-blue-500 to-blue-600 text-white`
    case "double-letter":
      return `${baseStyles} bg-gradient-to-br from-cyan-400 to-cyan-500 text-white`
    default:
      return `${baseStyles} bg-green-50 hover:bg-green-100 text-gray-600`
  }
}

const getSquareLabel = (type: SquareType) => {
  switch (type) {
    case "center":
      return "★"
    case "triple-word":
      return "3W"
    case "double-word":
      return "2W"
    case "triple-letter":
      return "3L"
    case "double-letter":
      return "2L"
    default:
      return ""
  }
}

export default function ScrabbleBoard({ onBoardChange, availableLetters }: ScrabbleBoardProps) {
  const [board, setBoard] = useState<BoardSquare[][]>(() => {
    return Array(BOARD_SIZE)
      .fill(null)
      .map((_, row) =>
        Array(BOARD_SIZE)
          .fill(null)
          .map((_, col) => ({
            type: getPremiumSquareType(row, col),
            letter: "",
            isPlaced: false,
            isPermanent: false,
          })),
      )
  })

  const [selectedLetter, setSelectedLetter] = useState<string>("")
  const [placedLetters, setPlacedLetters] = useState<string[]>([])

  const availableLettersArray = availableLetters.split("").filter((letter) => letter.trim())
  const remainingLetters = availableLettersArray.filter(
    (letter) =>
      !placedLetters.includes(letter) ||
      placedLetters.filter((l) => l === letter).length < availableLettersArray.filter((l) => l === letter).length,
  )

  const handleSquareClick = (row: number, col: number) => {
    if (!selectedLetter) return

    const newBoard = [...board]
    const square = newBoard[row][col]

    // If square already has a letter, remove it first
    if (square.letter && square.isPlaced && !square.isPermanent) {
      setPlacedLetters((prev) => {
        const index = prev.indexOf(square.letter)
        if (index > -1) {
          const newPlaced = [...prev]
          newPlaced.splice(index, 1)
          return newPlaced
        }
        return prev
      })
    }

    // Place the new letter
    square.letter = selectedLetter
    square.isPlaced = true
    square.isPermanent = false

    setBoard(newBoard)
    setPlacedLetters((prev) => [...prev, selectedLetter])
    setSelectedLetter("")

    onBoardChange?.(newBoard)
  }

  const clearBoard = () => {
    const newBoard = board.map((row) =>
      row.map((square) => ({
        ...square,
        letter: square.isPermanent ? square.letter : "",
        isPlaced: square.isPermanent,
      })),
    )
    setBoard(newBoard)
    setPlacedLetters([])
    setSelectedLetter("")
    onBoardChange?.(newBoard)
  }

  const addSampleWord = () => {
    // Add a sample word "HELLO" starting from center
    const newBoard = [...board]
    const word = "HELLO"
    const startRow = 7
    const startCol = 5

    word.split("").forEach((letter, index) => {
      if (startCol + index < BOARD_SIZE) {
        newBoard[startRow][startCol + index] = {
          ...newBoard[startRow][startCol + index],
          letter,
          isPlaced: true,
          isPermanent: true,
        }
      }
    })

    setBoard(newBoard)
    onBoardChange?.(newBoard)
  }

  return (
    <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Interactive Scrabble Board</span>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={addSampleWord}>
              <Sparkles className="w-4 h-4 mr-1" />
              Sample
            </Button>
            <Button variant="outline" size="sm" onClick={clearBoard}>
              <Trash2 className="w-4 h-4 mr-1" />
              Clear
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Letter Selection */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Available Letters</h3>
          <div className="flex flex-wrap gap-2">
            {remainingLetters.map((letter, index) => (
              <Button
                key={`${letter}-${index}`}
                variant={selectedLetter === letter ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedLetter(selectedLetter === letter ? "" : letter)}
                className="w-10 h-10 p-0 font-mono font-bold"
              >
                {letter}
              </Button>
            ))}
            {remainingLetters.length === 0 && <p className="text-sm text-muted-foreground">All letters placed</p>}
          </div>
          {selectedLetter && <p className="text-sm text-blue-600">Click on the board to place "{selectedLetter}"</p>}
        </div>

        {/* Board */}
        <div className="flex justify-center">
          <div className="inline-block p-2 bg-gray-100 rounded-lg shadow-inner">
            <div className="grid grid-cols-15 gap-0.5 bg-gray-200 p-1 rounded">
              {board.map((row, rowIndex) =>
                row.map((square, colIndex) => (
                  <button
                    key={`${rowIndex}-${colIndex}`}
                    className={getSquareStyles(square.type, square.isPlaced)}
                    onClick={() => handleSquareClick(rowIndex, colIndex)}
                    disabled={!selectedLetter && !square.isPlaced}
                  >
                    {square.letter || getSquareLabel(square.type)}
                  </button>
                )),
              )}
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-gradient-to-br from-red-500 to-red-600 rounded"></div>
            <span>Triple Word</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-gradient-to-br from-pink-400 to-pink-500 rounded"></div>
            <span>Double Word</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-gradient-to-br from-blue-500 to-blue-600 rounded"></div>
            <span>Triple Letter</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-gradient-to-br from-cyan-400 to-cyan-500 rounded"></div>
            <span>Double Letter</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-gradient-to-br from-pink-400 to-red-500 rounded"></div>
            <span>Center Star</span>
          </div>
        </div>

        {/* Board Statistics */}
        <div className="flex flex-wrap gap-4 text-sm">
          <Badge variant="secondary">Letters Placed: {placedLetters.length}</Badge>
          <Badge variant="secondary">Remaining: {remainingLetters.length}</Badge>
        </div>
      </CardContent>
    </Card>
  )
}
