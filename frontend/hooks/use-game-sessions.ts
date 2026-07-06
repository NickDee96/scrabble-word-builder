"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { WordResult } from "@/lib/scoring"

export interface GameSession {
  id: string
  name: string
  letters: string
  boardLetters: string
  results: WordResult[]
  createdAt: number
  updatedAt: number
}

const STORAGE_KEY = "scrabble.sessions.v1"

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `s_${Date.now()}_${Math.random().toString(36).slice(2)}`
}

function createSession(name: string): GameSession {
  const now = Date.now()
  return { id: newId(), name, letters: "", boardLetters: "", results: [], createdAt: now, updatedAt: now }
}

/**
 * Manages multiple game sessions persisted to localStorage. Each session holds its own
 * rack, board letters, and results, and the user can create/switch/rename/delete them.
 */
export function useGameSessions() {
  const [sessions, setSessions] = useState<GameSession[]>([])
  const [activeId, setActiveId] = useState<string>("")
  const [hydrated, setHydrated] = useState(false)

  // Load once on the client (avoids SSR/localStorage hydration mismatch).
  useEffect(() => {
    let loaded: GameSession[] | null = null
    let storedActive = ""
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw) as { sessions?: GameSession[]; activeId?: string }
        if (parsed.sessions && parsed.sessions.length > 0) {
          loaded = parsed.sessions
          storedActive = parsed.activeId ?? ""
        }
      }
    } catch {
      /* ignore corrupt storage */
    }
    if (!loaded) {
      const first = createSession("Game 1")
      loaded = [first]
      storedActive = first.id
    }
    setSessions(loaded)
    setActiveId(loaded.some((s) => s.id === storedActive) ? storedActive : loaded[0].id)
    setHydrated(true)
  }, [])

  // Persist on change.
  useEffect(() => {
    if (!hydrated) return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessions, activeId }))
    } catch {
      /* storage full / unavailable — ignore */
    }
  }, [sessions, activeId, hydrated])

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeId) ?? sessions[0],
    [sessions, activeId],
  )

  const updateActive = useCallback(
    (patch: Partial<GameSession>) => {
      setSessions((prev) =>
        prev.map((s) => (s.id === activeId ? { ...s, ...patch, updatedAt: Date.now() } : s)),
      )
    },
    [activeId],
  )

  const addSession = useCallback(() => {
    setSessions((prev) => {
      const next = createSession(`Game ${prev.length + 1}`)
      setActiveId(next.id)
      return [...prev, next]
    })
  }, [])

  const switchSession = useCallback((id: string) => setActiveId(id), [])

  const renameSession = useCallback((id: string, name: string) => {
    const trimmed = name.trim() || "Untitled"
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, name: trimmed, updatedAt: Date.now() } : s)))
  }, [])

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const filtered = prev.filter((s) => s.id !== id)
        if (filtered.length === 0) {
          const fresh = createSession("Game 1")
          setActiveId(fresh.id)
          return [fresh]
        }
        setActiveId((current) => (current === id ? filtered[0].id : current))
        return filtered
      })
    },
    [],
  )

  return {
    sessions,
    activeSession,
    activeId,
    hydrated,
    addSession,
    switchSession,
    renameSession,
    deleteSession,
    updateActive,
  }
}
