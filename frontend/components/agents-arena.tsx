"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, BarChart3, Play, Pause, RotateCcw, StepForward, Swords, Trophy } from "lucide-react"
import {
  BOARD_SIZE,
  cellLabel,
  parseBoardText,
  premiumClasses,
  premiumLabel,
  premiumType,
} from "@/lib/board"

type AgentType = "equity" | "score" | "simulation"

interface GameState {
  board: string
  racks: { A: string; B: string }
  bag: string
  scores: { A: number; B: number }
  turn: "A" | "B"
  passes: number
  moveNumber: number
  over: boolean
  winner: "A" | "B" | "tie" | null
}

interface MoveInfo {
  type: "play" | "exchange" | "pass" | "none"
  player: "A" | "B"
  agent: string
  word: string
  row: number
  col: number
  direction: string
  score: number
  leave: string
  equity: number | null
  winPct: number | null
  iterations: number | null
  tiles: { row: number; col: number; letter: string; blank: boolean }[]
}

const AGENT_LABEL: Record<AgentType, string> = {
  equity: "Equity",
  score: "Score",
  simulation: "Monte-Carlo",
}

const PLAYER_ACCENT: Record<"A" | "B", string> = {
  A: "bg-blue-600",
  B: "bg-purple-600",
}

interface BatchStats {
  games: number
  aWins: number
  bWins: number
  ties: number
  aTotal: number
  bTotal: number
  marginTotal: number
  failed: number
}

const pct = (n: number, d: number) => (d ? Math.round((n / d) * 100) : 0)

export default function AgentsArena() {
  const [game, setGame] = useState<GameState | null>(null)
  const [log, setLog] = useState<MoveInfo[]>([])
  const [agentA, setAgentA] = useState<AgentType>("equity")
  const [agentB, setAgentB] = useState<AgentType>("simulation")
  const [budget, setBudget] = useState(2000)
  const [running, setRunning] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastTiles, setLastTiles] = useState<Set<string>>(new Set())
  const [numGames, setNumGames] = useState(20)
  const [batchSeed, setBatchSeed] = useState("")
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchDone, setBatchDone] = useState(0)
  const [stats, setStats] = useState<BatchStats | null>(null)

  const runningRef = useRef(false)
  const gameRef = useRef<GameState | null>(null)
  const agentsRef = useRef({ A: agentA, B: agentB })
  const budgetRef = useRef(budget)
  const batchRunningRef = useRef(false)

  useEffect(() => {
    gameRef.current = game
  }, [game])
  useEffect(() => {
    agentsRef.current = { A: agentA, B: agentB }
  }, [agentA, agentB])
  useEffect(() => {
    budgetRef.current = budget
  }, [budget])
  useEffect(() => () => {
    runningRef.current = false
    batchRunningRef.current = false
  }, [])

  const board = game ? parseBoardText(game.board) : null

  const newGame = async () => {
    runningRef.current = false
    setRunning(false)
    setBusy(true)
    setError(null)
    try {
      const res = await fetch("/api/selfplay/new", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      })
      if (!res.ok) throw new Error(`status ${res.status}`)
      const state = (await res.json()) as GameState
      setGame(state)
      gameRef.current = state
      setLog([])
      setLastTiles(new Set())
    } catch {
      setError("Could not start a game. Is the server running?")
    } finally {
      setBusy(false)
    }
  }

  const doStep = async (): Promise<GameState | null> => {
    const current = gameRef.current
    if (!current || current.over) return null
    const res = await fetch("/api/selfplay/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        state: current,
        agents: agentsRef.current,
        timeBudgetMs: budgetRef.current,
        maxCandidates: 8,
      }),
    })
    if (!res.ok) {
      setError(
        res.status === 429
          ? "Slowing down — the server is rate-limiting turns. Try again in a moment."
          : `Turn failed (status ${res.status}).`,
      )
      return null
    }
    const data = (await res.json()) as { state: GameState; move: MoveInfo }
    setGame(data.state)
    gameRef.current = data.state
    setLog((l) => [...l, data.move])
    setLastTiles(new Set((data.move.tiles ?? []).map((t) => `${t.row},${t.col}`)))
    return data.state
  }

  const stepOnce = async () => {
    if (busy || running) return
    setBusy(true)
    setError(null)
    await doStep()
    setBusy(false)
  }

  const runLoop = async () => {
    while (runningRef.current) {
      const next = await doStep()
      if (!next || next.over) break
      await new Promise((r) => setTimeout(r, 450))
    }
    runningRef.current = false
    setRunning(false)
  }

  const startAuto = () => {
    if (!game || game.over || busy) return
    setError(null)
    runningRef.current = true
    setRunning(true)
    runLoop()
  }

  const stopAuto = () => {
    runningRef.current = false
    setRunning(false)
  }

  const runBatch = async () => {
    if (batchRunning) return
    runningRef.current = false
    setRunning(false)
    const n = Math.max(1, Math.min(numGames || 1, 100))
    // Full Monte-Carlo games are long; cap their per-move budget so each game finishes
    // within the dev proxy's request window. Fast agents (equity/score) are unaffected.
    const mcCount = [agentsRef.current.A, agentsRef.current.B].filter(
      (a) => a === "simulation",
    ).length
    const gameBudget =
      mcCount === 0 ? budgetRef.current : Math.min(budgetRef.current, mcCount === 2 ? 500 : 800)
    // Optional base seed makes the whole batch reproducible (each game gets a distinct
    // seed derived from it); blank = fresh random games every run.
    const seedTrim = batchSeed.trim()
    const seedBase = seedTrim === "" ? null : Number(seedTrim)

    batchRunningRef.current = true
    setBatchRunning(true)
    setError(null)
    setBatchDone(0)
    const acc: BatchStats = {
      games: 0, aWins: 0, bWins: 0, ties: 0, aTotal: 0, bTotal: 0, marginTotal: 0, failed: 0,
    }
    setStats({ ...acc })

    // Run the batch as parallel sub-batches on the backend (/api/selfplay/games): each
    // request plays up to `chunkSize` games across worker processes and returns them all,
    // so the run needs ~ceil(n / chunkSize) requests instead of n sequential ones. Chunks
    // stay small (and even, to keep the first-move A/B alternation aligned) so no single
    // request outruns the dev-proxy window; Monte-Carlo games are slow, so they chunk smaller.
    const seedRoot =
      seedBase !== null && Number.isFinite(seedBase) ? Math.trunc(seedBase) * 1000 : null
    const chunkSize = mcCount > 0 ? 4 : 8

    const runChunk = async (start: number, size: number) => {
      const body: Record<string, unknown> = {
        agents: agentsRef.current,
        timeBudgetMs: gameBudget,
        maxCandidates: 8,
        count: size,
        alternateFirst: true,
      }
      if (seedRoot !== null) body.seed = seedRoot + start
      for (let attempt = 0; attempt < 2 && batchRunningRef.current; attempt++) {
        try {
          const res = await fetch("/api/selfplay/games", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          })
          if (res.ok) {
            const data = (await res.json()) as {
              games: { scores: { A: number; B: number }; winner: "A" | "B" | "tie" }[]
            }
            return data.games
          }
          if (res.status === 429) await new Promise((r) => setTimeout(r, 1500))
        } catch {
          /* network hiccup - retry once */
        }
      }
      return null
    }

    for (let start = 0; start < n && batchRunningRef.current; start += chunkSize) {
      const size = Math.min(chunkSize, n - start)
      const games = await runChunk(start, size)
      if (!batchRunningRef.current) break
      if (games === null) {
        acc.failed += size
      } else {
        for (const g of games) {
          acc.games += 1
          acc.aTotal += g.scores.A
          acc.bTotal += g.scores.B
          acc.marginTotal += g.scores.A - g.scores.B
          if (g.winner === "A") acc.aWins += 1
          else if (g.winner === "B") acc.bWins += 1
          else acc.ties += 1
        }
      }
      setStats({ ...acc })
      setBatchDone(Math.min(start + size, n))
    }
    if (acc.games === 0 && acc.failed > 0) {
      setError(
        "Games kept failing \u2014 Monte-Carlo games can be too slow for the dev proxy. Try a lower MC time, fewer games, or a non-MC matchup.",
      )
    }
    batchRunningRef.current = false
    setBatchRunning(false)
  }

  const stopBatch = () => {
    batchRunningRef.current = false
    setBatchRunning(false)
  }

  const agentToggle = (
    value: AgentType,
    onChange: (v: AgentType) => void,
    accent: string,
  ) => (
    <div className="inline-flex rounded-md border overflow-hidden text-xs">
      {(["equity", "score", "simulation"] as AgentType[]).map((t) => (
        <button
          key={t}
          type="button"
          disabled={running || batchRunning}
          onClick={() => onChange(t)}
          className={`px-2 py-1 disabled:opacity-60 ${
            value === t ? `${accent} text-white` : "bg-white hover:bg-muted"
          }`}
        >
          {AGENT_LABEL[t]}
        </button>
      ))}
    </div>
  )

  const rackTiles = (rack: string) => (
    <div className="flex flex-wrap gap-1">
      {rack.split("").map((ch, i) => (
        <span
          key={i}
          className="w-7 h-7 rounded border border-yellow-400 bg-yellow-100 text-gray-800 text-sm font-bold flex items-center justify-center"
        >
          {ch === "?" ? "␣" : ch}
        </span>
      ))}
      {rack.length === 0 && <span className="text-xs text-muted-foreground">empty</span>}
    </div>
  )

  const scoreCard = (who: "A" | "B", agent: AgentType) => {
    const active = game && !game.over && game.turn === who
    return (
      <div
        className={`rounded-lg border p-3 space-y-2 transition-colors ${
          active ? "ring-2 ring-offset-1 " + (who === "A" ? "ring-blue-500" : "ring-purple-500") : ""
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${PLAYER_ACCENT[who]}`} />
            <span className="font-semibold">Agent {who}</span>
            <Badge variant="outline" className="text-[10px]">
              {AGENT_LABEL[agent]}
            </Badge>
          </span>
          <span className="text-2xl font-bold tabular-nums">{game?.scores[who] ?? 0}</span>
        </div>
        {game && rackTiles(game.racks[who])}
        {active && busy && (
          <span className="text-xs text-muted-foreground">thinking…</span>
        )}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-6">
      {/* Board */}
      <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Swords className="w-5 h-5 text-purple-600" /> Agents Arena
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Pit an <b>Equity</b>, <b>Score</b>, or <b>Monte-Carlo</b> agent against each other. Pick
            each side, then step or auto-play.
          </p>
        </CardHeader>
        <CardContent>
          {board ? (
            <div className="flex justify-center">
              <div
                className="inline-grid gap-0.5 bg-gray-200 p-1 rounded"
                style={{ gridTemplateColumns: `repeat(${BOARD_SIZE}, minmax(0, 1fr))` }}
              >
                {board.map((rowCells, row) =>
                  rowCells.map((cell, col) => {
                    const type = premiumType(row, col)
                    let content = premiumLabel(type)
                    let classes = premiumClasses(type)
                    if (cell) {
                      content = cell.letter
                      classes = cell.blank
                        ? "bg-purple-200 text-purple-800 border-purple-400"
                        : "bg-yellow-100 text-gray-800 border-yellow-400"
                    }
                    const fresh = lastTiles.has(`${row},${col}`)
                    return (
                      <div
                        key={`${row}-${col}`}
                        className={`w-6 h-6 sm:w-7 sm:h-7 md:w-8 md:h-8 border text-[9px] sm:text-[11px] font-bold flex items-center justify-center ${classes} ${
                          fresh ? "ring-2 ring-emerald-500 z-10" : "border-gray-300"
                        }`}
                      >
                        {content}
                      </div>
                    )
                  }),
                )}
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
              Press <b className="mx-1">New game</b> to deal a board.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Controls + log */}
      <div className="space-y-4">
        <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Match</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground w-14 shrink-0">Agent A</Label>
                {agentToggle(agentA, setAgentA, "bg-blue-600")}
              </div>
              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground w-14 shrink-0">Agent B</Label>
                {agentToggle(agentB, setAgentB, "bg-purple-600")}
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <Label className="text-muted-foreground">MC time / move</Label>
              <select
                value={budget}
                disabled={running || batchRunning}
                onChange={(e) => setBudget(Number(e.target.value))}
                aria-label="Monte-Carlo time per move"
                className="h-8 rounded-md border bg-white px-2 disabled:opacity-60"
              >
                <option value={1000}>1s</option>
                <option value={2000}>2s</option>
                <option value={3000}>3s</option>
                <option value={5000}>5s</option>
              </select>
              <span className="text-muted-foreground">(Monte-Carlo only)</span>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={newGame} disabled={busy || batchRunning} variant="outline">
                <RotateCcw className="w-4 h-4 mr-1" /> New game
              </Button>
              <Button onClick={stepOnce} disabled={!game || game.over || busy || running || batchRunning} variant="outline">
                <StepForward className="w-4 h-4 mr-1" /> Step
              </Button>
              {running ? (
                <Button onClick={stopAuto} className="bg-red-600 hover:bg-red-700">
                  <Pause className="w-4 h-4 mr-1" /> Stop
                </Button>
              ) : (
                <Button
                  onClick={startAuto}
                  disabled={!game || game.over || busy || batchRunning}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                >
                  <Play className="w-4 h-4 mr-1" /> Auto-play
                </Button>
              )}
            </div>

            {game && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {scoreCard("A", agentA)}
                {scoreCard("B", agentB)}
              </div>
            )}

            {game && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>
                  Move <b>{game.moveNumber}</b>
                </span>
                <span>
                  Bag <b>{game.bag.length}</b>
                </span>
                {!game.over && (
                  <span>
                    To move: <b>Agent {game.turn}</b>
                  </span>
                )}
              </div>
            )}

            {game?.over && (
              <Alert className="bg-white/70 border-emerald-300">
                <Trophy className="h-4 w-4 text-yellow-500" />
                <AlertTitle>
                  {game.winner === "tie"
                    ? "It's a tie!"
                    : `Agent ${game.winner} wins (${AGENT_LABEL[game.winner === "A" ? agentA : agentB]})`}
                </AlertTitle>
                <AlertDescription>
                  Final score — A {game.scores.A} · B {game.scores.B}
                </AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive" className="bg-white/70">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Problem</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Head-to-head batch */}
        <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-emerald-600" /> Head-to-head
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Run a batch — {AGENT_LABEL[agentA]} (A) vs {AGENT_LABEL[agentB]} (B), alternating who
              starts each game for fairness.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Label htmlFor="num-games" className="text-xs text-muted-foreground">
                Games
              </Label>
              <Input
                id="num-games"
                type="number"
                min={1}
                max={100}
                value={numGames}
                disabled={batchRunning}
                onChange={(e) => setNumGames(Math.max(1, Math.min(Number(e.target.value) || 1, 100)))}
                className="h-8 w-20"
              />
              <Label htmlFor="batch-seed" className="text-xs text-muted-foreground">
                Seed
              </Label>
              <Input
                id="batch-seed"
                type="number"
                placeholder="random"
                value={batchSeed}
                disabled={batchRunning}
                onChange={(e) => setBatchSeed(e.target.value)}
                className="h-8 w-24"
              />
              {batchRunning ? (
                <Button onClick={stopBatch} className="bg-red-600 hover:bg-red-700">
                  <Pause className="w-4 h-4 mr-1" /> Stop
                </Button>
              ) : (
                <Button
                  onClick={runBatch}
                  disabled={busy || running}
                  className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
                >
                  <Play className="w-4 h-4 mr-1" /> Run {numGames} games
                </Button>
              )}
              {(batchRunning || (stats && (stats.games > 0 || stats.failed > 0))) && (
                <span className="text-xs text-muted-foreground tabular-nums">
                  {batchDone}/{numGames}
                  {batchRunning ? " …" : ""}
                  {stats && stats.failed > 0 ? ` · ${stats.failed} failed` : ""}
                </span>
              )}
            </div>

            {(agentA === "simulation" || agentB === "simulation") && (
              <p className="text-[11px] text-amber-600">
                Monte-Carlo games are slow (~{(budget / 1000).toFixed(0)}s per move); a large batch
                can take several minutes.
              </p>
            )}

            {batchRunning && (
              <div className="h-1.5 w-full rounded bg-muted overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all"
                  style={{ width: `${(batchDone / Math.max(1, numGames)) * 100}%` }}
                />
              </div>
            )}

            {stats && stats.games > 0 && (
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg border p-2">
                    <div className="text-[11px] text-muted-foreground truncate">
                      A · {AGENT_LABEL[agentA]}
                    </div>
                    <div className="text-2xl font-bold text-blue-600 tabular-nums">{stats.aWins}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {pct(stats.aWins, stats.games)}% wins
                    </div>
                  </div>
                  <div className="rounded-lg border p-2">
                    <div className="text-[11px] text-muted-foreground">Ties</div>
                    <div className="text-2xl font-bold tabular-nums">{stats.ties}</div>
                    <div className="text-[11px] text-muted-foreground">of {stats.games}</div>
                  </div>
                  <div className="rounded-lg border p-2">
                    <div className="text-[11px] text-muted-foreground truncate">
                      B · {AGENT_LABEL[agentB]}
                    </div>
                    <div className="text-2xl font-bold text-purple-600 tabular-nums">{stats.bWins}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {pct(stats.bWins, stats.games)}% wins
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>
                    Avg score — A <b>{(stats.aTotal / stats.games).toFixed(1)}</b> · B{" "}
                    <b>{(stats.bTotal / stats.games).toFixed(1)}</b>
                  </span>
                  <span>
                    Avg margin (A−B) <b>{(stats.marginTotal / stats.games).toFixed(1)}</b>
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {log.length > 0 && (
          <Card className="shadow-lg border-0 bg-white/70 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Move log</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1 max-h-[22rem] overflow-y-auto pr-1">
                {log
                  .map((m, i) => ({ m, i }))
                  .reverse()
                  .map(({ m, i }) => (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-2 p-1.5 rounded border bg-white/60 text-sm"
                    >
                      <span className="flex items-center gap-2 min-w-0">
                        <span className="text-[10px] text-muted-foreground w-5 text-right">
                          {i + 1}.
                        </span>
                        <Badge className={`${PLAYER_ACCENT[m.player]} text-white text-[10px]`}>
                          {m.player}
                        </Badge>
                        {m.type === "play" ? (
                          <span className="font-mono font-semibold truncate">{m.word}</span>
                        ) : (
                          <span className="italic text-muted-foreground">{m.type}</span>
                        )}
                      </span>
                      <span className="flex items-center gap-2 flex-none text-xs text-muted-foreground">
                        {m.type === "play" && (
                          <>
                            <span className="hidden sm:inline">
                              {cellLabel(m.row, m.col)} · {m.direction}
                            </span>
                            {m.winPct != null ? (
                              <span className="tabular-nums">{Math.round(m.winPct * 100)}%</span>
                            ) : m.equity != null ? (
                              <span className="tabular-nums">eq {m.equity.toFixed(1)}</span>
                            ) : null}
                            <Badge variant="secondary" className="tabular-nums">
                              +{m.score}
                            </Badge>
                          </>
                        )}
                      </span>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
