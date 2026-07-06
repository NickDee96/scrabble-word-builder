"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Search, Shuffle, Trophy, Zap, BookOpen, Target, Grid3X3, AlertCircle, SearchX, Swords } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import AnalyzeBoard from "@/components/analyze-board"
import AgentsArena from "@/components/agents-arena"
import { getScoreColor, groupResultsByLength, type WordResult } from "@/lib/scoring"
import { emptyBoard, type BoardCell, type GameMove, type Play } from "@/lib/board"
import { useGameSessions } from "@/hooks/use-game-sessions"
import SessionBar from "@/components/session-bar"

export default function ScrabbleWordBuilder() {
  const {
    sessions,
    activeSession,
    activeId,
    hydrated,
    addSession,
    switchSession,
    renameSession,
    deleteSession,
    updateActive,
  } = useGameSessions()

  const letters = activeSession?.letters ?? ""
  const boardLetters = activeSession?.boardLetters ?? ""
  const results = activeSession?.results ?? []
  const boardCells = activeSession?.boardCells ?? emptyBoard()
  const plays = activeSession?.plays ?? []
  const moveLog = activeSession?.moveLog ?? []
  const setLetters = (value: string) => updateActive({ letters: value })
  const setBoardLetters = (value: string) => updateActive({ boardLetters: value })
  const setResults = (value: WordResult[]) => updateActive({ results: value })
  const setBoardCells = (value: (BoardCell | null)[][]) => updateActive({ boardCells: value })
  const setPlays = (value: Play[]) => updateActive({ plays: value })
  const setMoveLog = (value: GameMove[]) => updateActive({ moveLog: value })

  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState("builder")
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)

  // Reset transient UI state when switching between game sessions.
  useEffect(() => {
    setIsLoading(false)
    setError(null)
    setHasSearched(false)
  }, [activeId])

  // Function to find words by calling the backend API. The request uses a
  // same-origin relative URL that Next.js rewrites proxy to the backend, so the
  // same build works locally and in Docker without hardcoded hosts or CORS.
  const findWords = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/find-words', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          letters: letters,
          boardLetters: boardLetters,
        }),
      })

      if (!response.ok) {
        let detail = `Request failed (status ${response.status}).`
        if (response.status === 429) {
          detail = "You're searching too fast — please wait a moment and try again."
        } else {
          try {
            const body = await response.json()
            if (typeof body?.detail === "string") detail = body.detail
          } catch {
            /* ignore non-JSON error bodies */
          }
        }
        setResults([])
        setError(detail)
        return
      }

      const data = await response.json()
      setResults(data.success ? data.results : [])
      if (!data.success) {
        setError("Something went wrong finding words. Please try again.")
      }
    } catch (err) {
      console.error('Error finding words:', err)
      setResults([])
      setError("Could not reach the server. Check your connection and try again.")
    } finally {
      setHasSearched(true)
      setIsLoading(false)
    }
  }

  const clearForm = () => {
    setLetters("")
    setBoardLetters("")
    setResults([])
    setError(null)
    setHasSearched(false)
  }

  const groupedResults = groupResultsByLength(results)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Scrabble Word Builder
                </h1>
                <p className="text-sm text-muted-foreground">Find the perfect words for your game</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className="hidden sm:flex">
                <Trophy className="w-3 h-3 mr-1" />
                279,496 Words
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {hydrated && (
          <div className="mb-6">
            <SessionBar
              sessions={sessions}
              activeId={activeId}
              onSwitch={switchSession}
              onAdd={addSession}
              onRename={renameSession}
              onDelete={deleteSession}
            />
          </div>
        )}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-8">
            <TabsTrigger value="builder" className="flex items-center space-x-2">
              <Search className="w-4 h-4" />
              <span>Word Builder</span>
            </TabsTrigger>
            <TabsTrigger value="board" className="flex items-center space-x-2">
              <Grid3X3 className="w-4 h-4" />
              <span>Board Analyzer</span>
            </TabsTrigger>
            <TabsTrigger value="arena" className="flex items-center space-x-2">
              <Swords className="w-4 h-4" />
              <span>Agents Arena</span>
            </TabsTrigger>
            <TabsTrigger value="strategy" className="flex items-center space-x-2">
              <Target className="w-4 h-4" />
              <span>Strategy Tips</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="builder" className="space-y-8">
            {/* Input Section */}
            <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center space-x-2">
                  <Zap className="w-5 h-5 text-blue-600" />
                  <span>Enter Your Letters</span>
                </CardTitle>
                <CardDescription>
                  Input your available letters and any board letters to find the best possible words
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="letters" className="text-sm font-medium">
                      Your Letters
                    </Label>
                    <Input
                      id="letters"
                      placeholder="e.g., WERTASH"
                      value={letters}
                      onChange={(e) => setLetters(e.target.value.toUpperCase())}
                      className="text-lg font-mono tracking-wider"
                    />
                    <p className="text-xs text-muted-foreground">Use spaces for blank tiles</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="boardLetters" className="text-sm font-medium">
                      Board Letters (Optional)
                    </Label>
                    <Input
                      id="boardLetters"
                      placeholder="e.g., BAK"
                      value={boardLetters}
                      onChange={(e) => setBoardLetters(e.target.value.toUpperCase())}
                      className="text-lg font-mono tracking-wider"
                    />
                    <p className="text-xs text-muted-foreground">Letters already on the board</p>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    onClick={findWords}
                    disabled={!letters.trim() || isLoading}
                    className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                        Finding Words...
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4 mr-2" />
                        Find Words
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={clearForm} className="flex-none">
                    <Shuffle className="w-4 h-4 mr-2" />
                    Clear
                  </Button>
                </div>
              </CardContent>
            </Card>

            {error && (
              <Alert variant="destructive" className="bg-white/70 backdrop-blur-sm">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Couldn't find words</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {hasSearched && !isLoading && !error && results.length === 0 && (
              <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                  <SearchX className="w-10 h-10 text-muted-foreground" />
                  <div>
                    <p className="font-semibold">No words found</p>
                    <p className="text-sm text-muted-foreground">
                      Try different letters, or add board letters to build around.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Results Section */}
            {results.length > 0 && (
              <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Found Words</span>
                    <Badge variant="secondary">{results.length} words found</Badge>
                  </CardTitle>
                  <CardDescription>Words are grouped by length and sorted by score</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {Object.entries(groupedResults)
                      .sort(([a], [b]) => Number.parseInt(b) - Number.parseInt(a))
                      .map(([length, words]) => (
                        <div key={length} className="space-y-3">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-lg font-semibold">{length}-Letter Words</h3>
                            <Badge variant="outline">{words.length} found</Badge>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                            {words
                              .sort((a, b) => b.score - a.score || a.word.localeCompare(b.word))
                              .map((result, index) => (
                                <div
                                  key={index}
                                  className="flex items-center justify-between p-3 rounded-lg border bg-white/50 hover:bg-white/80 transition-colors"
                                >
                                  <span className="font-mono font-semibold text-lg">{result.word}</span>
                                  <Badge className={`${getScoreColor(result.score)} text-white`}>{result.score}</Badge>
                                </div>
                              ))}
                          </div>
                          {length !== Object.keys(groupedResults)[Object.keys(groupedResults).length - 1] && (
                            <Separator className="mt-4" />
                          )}
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="board" className="space-y-6">
            <AnalyzeBoard
              key={activeId}
              board={boardCells}
              onBoardChange={setBoardCells}
              rack={letters}
              onRackChange={setLetters}
              plays={plays}
              onPlaysChange={setPlays}
              moveLog={moveLog}
              onMoveLogChange={setMoveLog}
            />
          </TabsContent>

          <TabsContent value="arena" className="space-y-6">
            <AgentsArena />
          </TabsContent>

          <TabsContent value="strategy" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-lg">High-Value Letters</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span>Q, Z</span>
                      <Badge className="bg-red-500 text-white">10 points</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>J, X</span>
                      <Badge className="bg-orange-500 text-white">8 points</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>K</span>
                      <Badge className="bg-yellow-500 text-white">5 points</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>F, H, V, W, Y</span>
                      <Badge className="bg-blue-500 text-white">4 points</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-lg">Pro Tips</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                      <span>Use blank tiles strategically for high-value letters</span>
                    </div>
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                      <span>Look for opportunities to use premium squares</span>
                    </div>
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                      <span>Consider parallel plays to maximize points</span>
                    </div>
                    <div className="flex items-start space-x-2">
                      <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                      <span>Keep a balanced rack with vowels and consonants</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm md:col-span-2">
                <CardHeader>
                  <CardTitle className="text-lg">Premium Square Strategy</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div className="space-y-2">
                      <h4 className="font-semibold text-red-600">Triple Word Score</h4>
                      <p>Located at corners and center. Triples the entire word score.</p>
                    </div>
                    <div className="space-y-2">
                      <h4 className="font-semibold text-pink-600">Double Word Score</h4>
                      <p>Doubles the entire word score. Great for medium-length words.</p>
                    </div>
                    <div className="space-y-2">
                      <h4 className="font-semibold text-blue-600">Triple Letter Score</h4>
                      <p>Triples individual letter value. Perfect for high-value letters.</p>
                    </div>
                    <div className="space-y-2">
                      <h4 className="font-semibold text-cyan-600">Double Letter Score</h4>
                      <p>Doubles individual letter value. Use with consonants.</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
