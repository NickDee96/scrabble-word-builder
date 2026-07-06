"use client"

import { useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Sparkles, Trash2, AlertCircle, Trophy, Copy, ClipboardPaste } from "lucide-react"
import {
  BOARD_SIZE,
  boardToText,
  cellLabel,
  emptyBoard,
  parseBoardText,
  premiumClasses,
  premiumLabel,
  premiumType,
  type BoardCell,
  type Play,
} from "@/lib/board"

interface AnalyzeBoardProps {
  board: (BoardCell | null)[][]
  onBoardChange: (board: (BoardCell | null)[][]) => void
  rack: string
  onRackChange: (rack: string) => void
  plays: Play[]
  onPlaysChange: (plays: Play[]) => void
}

export default function AnalyzeBoard({
  board,
  onBoardChange,
  rack,
  onRackChange,
  plays,
  onPlaysChange,
}: AnalyzeBoardProps) {
  const [selected, setSelected] = useState<{ row: number; col: number } | null>(null)
  const [hover, setHover] = useState<Play | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [pasteText, setPasteText] = useState("")
  const [copied, setCopied] = useState(false)
  const [mode, setMode] = useState<"equity" | "score">("equity")
  const gridRef = useRef<HTMLDivElement>(null)

  const ghost = useMemo(() => {
    const map = new Map<string, string>()
    if (hover) for (const t of hover.tiles) map.set(`${t.row},${t.col}`, t.letter)
    return map
  }, [hover])

  const setCell = (row: number, col: number, cell: BoardCell | null) => {
    const next = board.map((r) => r.slice())
    next[row][col] = cell
    onBoardChange(next)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!selected) return
    const { row, col } = selected
    if (/^[a-zA-Z]$/.test(e.key)) {
      e.preventDefault()
      setCell(row, col, { letter: e.key.toUpperCase(), blank: e.shiftKey })
      if (col < BOARD_SIZE - 1) setSelected({ row, col: col + 1 })
    } else if (e.key === "Backspace" || e.key === "Delete") {
      e.preventDefault()
      setCell(row, col, null)
      if (e.key === "Backspace" && col > 0) setSelected({ row, col: col - 1 })
    } else if (e.key === "ArrowRight" && col < BOARD_SIZE - 1) {
      e.preventDefault(); setSelected({ row, col: col + 1 })
    } else if (e.key === "ArrowLeft" && col > 0) {
      e.preventDefault(); setSelected({ row, col: col - 1 })
    } else if (e.key === "ArrowUp" && row > 0) {
      e.preventDefault(); setSelected({ row: row - 1, col })
    } else if (e.key === "ArrowDown" && row < BOARD_SIZE - 1) {
      e.preventDefault(); setSelected({ row: row + 1, col })
    }
  }

  const analyze = async (useMode: "equity" | "score" = mode) => {
    setIsAnalyzing(true)
    setError(null)
    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ board, rack, maxResults: 20, mode: useMode }),
      })
      if (!response.ok) {
        let detail = `Request failed (status ${response.status}).`
        if (response.status === 429) {
          detail = "You're analyzing too fast — please wait a moment and try again."
        } else {
          try {
            const body = await response.json()
            if (typeof body?.detail === "string") detail = body.detail
          } catch {
            /* ignore */
          }
        }
        onPlaysChange([])
        setError(detail)
        return
      }
      const data = await response.json()
      onPlaysChange(data.plays ?? [])
      if ((data.plays ?? []).length === 0) {
        setError("No legal plays for this rack on this board.")
      }
    } catch {
      setError("Could not reach the server. Check your connection and try again.")
    } finally {
      setIsAnalyzing(false)
    }
  }

  const changeMode = (m: "equity" | "score") => {
    setMode(m)
    if (rack.trim() && plays.length > 0) analyze(m)
  }

  const commitPlay = (play: Play) => {
    const next = board.map((r) => r.slice())
    const rackArr = rack.split("")
    for (const t of play.tiles) {
      next[t.row][t.col] = { letter: t.letter, blank: t.blank }
      const idx = rackArr.indexOf(t.blank ? "?" : t.letter)
      if (idx >= 0) rackArr.splice(idx, 1)
    }
    onBoardChange(next)
    onRackChange(rackArr.join(""))
    onPlaysChange([])
    setHover(null)
    setSelected(null)
  }

  const clearBoard = () => {
    onBoardChange(emptyBoard())
    onPlaysChange([])
    setHover(null)
    setSelected(null)
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(boardToText(board))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable */
    }
  }

  const openPaste = () => {
    setPasteText(boardToText(board))
    setPasteOpen(true)
  }

  const loadPasted = () => {
    onBoardChange(parseBoardText(pasteText))
    onPlaysChange([])
    setHover(null)
    setSelected(null)
    setPasteOpen(false)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-6">
      <Dialog open={pasteOpen} onOpenChange={setPasteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Paste board position</DialogTitle>
            <DialogDescription>
              One character per square, up to 15 columns × 15 rows. Uppercase = a tile,
              lowercase = a blank tile, and <code>.</code> or a space = empty.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            rows={15}
            spellCheck={false}
            className="font-mono text-xs leading-tight whitespace-pre"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasteOpen(false)}>
              Cancel
            </Button>
            <Button onClick={loadPasted}>Load board</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Board editor */}
      <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2">
            <span>Board Position</span>
            <div className="flex items-center gap-1.5">
              <Button variant="outline" size="sm" onClick={handleCopy}>
                <Copy className="w-4 h-4 mr-1" /> {copied ? "Copied!" : "Copy"}
              </Button>
              <Button variant="outline" size="sm" onClick={openPaste}>
                <ClipboardPaste className="w-4 h-4 mr-1" /> Paste
              </Button>
              <Button variant="outline" size="sm" onClick={clearBoard}>
                <Trash2 className="w-4 h-4 mr-1" /> Clear
              </Button>
            </div>
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Click a square and type to enter the tiles already on the board. Hold{" "}
            <kbd className="px-1 rounded bg-muted">Shift</kbd> for a blank. Arrow keys move.
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center">
            <div
              ref={gridRef}
              tabIndex={0}
              onKeyDown={handleKeyDown}
              className="inline-grid gap-0.5 bg-gray-200 p-1 rounded outline-none"
              style={{ gridTemplateColumns: `repeat(${BOARD_SIZE}, minmax(0, 1fr))` }}
            >
              {board.map((rowCells, row) =>
                rowCells.map((cell, col) => {
                  const type = premiumType(row, col)
                  const ghostLetter = ghost.get(`${row},${col}`)
                  const isSelected = selected?.row === row && selected?.col === col
                  let content = premiumLabel(type)
                  let classes = premiumClasses(type)
                  if (cell) {
                    content = cell.letter
                    classes = cell.blank
                      ? "bg-yellow-50 text-gray-500 border-yellow-300"
                      : "bg-yellow-100 text-gray-800 border-yellow-400 shadow-sm"
                  } else if (ghostLetter) {
                    content = ghostLetter
                    classes = "bg-emerald-300 text-emerald-950 border-emerald-500"
                  }
                  return (
                    <button
                      key={`${row}-${col}`}
                      onClick={() => {
                        setSelected({ row, col })
                        gridRef.current?.focus()
                      }}
                      className={`w-6 h-6 sm:w-8 sm:h-8 md:w-9 md:h-9 border text-[10px] sm:text-xs font-bold flex items-center justify-center transition-colors ${classes} ${
                        isSelected ? "ring-2 ring-blue-600 ring-offset-1 z-10" : "border-gray-300"
                      }`}
                    >
                      {content}
                    </button>
                  )
                }),
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Rack + results */}
      <div className="space-y-4">
        <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Your Rack</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="analyze-rack" className="text-sm">
                Tiles on your rack
              </Label>
              <Input
                id="analyze-rack"
                value={rack}
                onChange={(e) => onRackChange(e.target.value.toUpperCase().replace(/[^A-Z?]/g, ""))}
                placeholder="e.g. AEINRST"
                maxLength={7}
                className="text-lg font-mono tracking-wider"
              />
              <p className="text-xs text-muted-foreground">Use ? for a blank tile.</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Rank by</span>
              <div className="inline-flex rounded-md border overflow-hidden">
                <button
                  type="button"
                  onClick={() => changeMode("equity")}
                  className={`px-2.5 py-1 ${mode === "equity" ? "bg-blue-600 text-white" : "bg-white hover:bg-muted"}`}
                >
                  Equity
                </button>
                <button
                  type="button"
                  onClick={() => changeMode("score")}
                  className={`px-2.5 py-1 ${mode === "score" ? "bg-blue-600 text-white" : "bg-white hover:bg-muted"}`}
                >
                  Score
                </button>
              </div>
              <span className="text-muted-foreground hidden sm:inline">= score + tiles kept</span>
            </div>
            <Button
              onClick={() => analyze()}
              disabled={!rack.trim() || isAnalyzing}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              {isAnalyzing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Analyzing…
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" /> Find best plays
                </>
              )}
            </Button>
            {error && (
              <Alert variant="destructive" className="bg-white/70">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Couldn&apos;t analyze</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {plays.length > 0 && (
          <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Trophy className="w-5 h-5 text-yellow-500" /> Best plays
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Ranked by {mode === "equity" ? "equity (score + leave)" : "score"}. Hover to preview; click to place.
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-1.5 max-h-[26rem] overflow-y-auto pr-1">
                {plays.map((play, i) => (
                  <button
                    key={`${play.word}-${play.row}-${play.col}-${play.direction}`}
                    onMouseEnter={() => setHover(play)}
                    onMouseLeave={() => setHover(null)}
                    onClick={() => commitPlay(play)}
                    className="w-full flex items-center justify-between gap-2 p-2 rounded-lg border bg-white/60 hover:bg-emerald-50 hover:border-emerald-300 transition-colors text-left"
                  >
                    <span className="flex items-center gap-2 min-w-0">
                      <span className="text-xs text-muted-foreground w-5 text-right">{i + 1}.</span>
                      <span className="font-mono font-semibold truncate">{play.word}</span>
                    </span>
                    <span className="flex items-center gap-2 flex-none text-xs text-muted-foreground">
                      <span>
                        {cellLabel(play.row, play.col)} · {play.direction}
                      </span>
                      <span className="hidden md:inline">
                        {play.leave ? `keep ${play.leave}` : "uses all"}
                      </span>
                      <span className="hidden sm:inline tabular-nums">
                        {mode === "equity" ? `${play.score} pts` : `eq ${play.equity.toFixed(1)}`}
                      </span>
                      <Badge className="bg-blue-600 text-white tabular-nums">
                        {mode === "equity" ? play.equity.toFixed(1) : play.score}
                      </Badge>
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
