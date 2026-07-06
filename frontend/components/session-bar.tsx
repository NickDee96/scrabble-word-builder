"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, X, Check, Pencil } from "lucide-react"
import type { GameSession } from "@/hooks/use-game-sessions"

interface SessionBarProps {
  sessions: GameSession[]
  activeId: string
  onSwitch: (id: string) => void
  onAdd: () => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
}

export default function SessionBar({
  sessions,
  activeId,
  onSwitch,
  onAdd,
  onRename,
  onDelete,
}: SessionBarProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState("")

  const startEdit = (s: GameSession) => {
    setEditingId(s.id)
    setDraft(s.name)
  }
  const commit = () => {
    if (editingId) onRename(editingId, draft)
    setEditingId(null)
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1">
      {sessions.map((s) => {
        const active = s.id === activeId
        const isEditing = editingId === s.id
        return (
          <div
            key={s.id}
            className={`group flex items-center gap-1 rounded-lg border px-2 py-1 whitespace-nowrap transition-colors ${
              active
                ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white border-transparent shadow"
                : "bg-white/70 hover:bg-white"
            }`}
          >
            {isEditing ? (
              <span className="flex items-center gap-1">
                <Input
                  value={draft}
                  autoFocus
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commit()
                    if (e.key === "Escape") setEditingId(null)
                  }}
                  onBlur={commit}
                  className="h-6 w-28 text-black"
                />
                <button onClick={commit} aria-label="Save name">
                  <Check className="w-4 h-4" />
                </button>
              </span>
            ) : (
              <>
                <button
                  onClick={() => onSwitch(s.id)}
                  onDoubleClick={() => startEdit(s)}
                  className="text-sm font-medium max-w-[10rem] truncate"
                  title={`${s.name} — double-click to rename`}
                >
                  {s.name}
                </button>
                <button
                  onClick={() => startEdit(s)}
                  aria-label="Rename session"
                  className={`opacity-0 group-hover:opacity-100 transition-opacity ${
                    active ? "text-white/90" : "text-muted-foreground"
                  }`}
                >
                  <Pencil className="w-3 h-3" />
                </button>
                <button
                  onClick={() => onDelete(s.id)}
                  aria-label="Delete session"
                  className={`opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-400 ${
                    active ? "text-white/90" : "text-muted-foreground"
                  }`}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        )
      })}
      <Button variant="outline" size="sm" onClick={onAdd} className="flex-none bg-white/70">
        <Plus className="w-4 h-4 mr-1" /> New game
      </Button>
    </div>
  )
}
