export const BOARD_SIZE = 15

export type PremiumType = "TW" | "DW" | "TL" | "DL" | "center" | "normal"

export interface BoardCell {
  letter: string
  blank: boolean
}

export interface AnalyzePlacedTile {
  row: number
  col: number
  letter: string
  blank: boolean
}

export interface Play {
  word: string
  row: number
  col: number
  direction: "across" | "down"
  score: number
  leave: string
  tiles: AnalyzePlacedTile[]
  crossWords: string[]
}

const TW = new Set(["0,0", "0,7", "0,14", "7,0", "7,14", "14,0", "14,7", "14,14"])
const DW = new Set([
  "1,1", "2,2", "3,3", "4,4", "1,13", "2,12", "3,11", "4,10",
  "13,1", "12,2", "11,3", "10,4", "13,13", "12,12", "11,11", "10,10",
])
const TL = new Set([
  "1,5", "1,9", "5,1", "5,5", "5,9", "5,13", "9,1", "9,5", "9,9", "9,13", "13,5", "13,9",
])
const DL = new Set([
  "0,3", "0,11", "2,6", "2,8", "3,0", "3,7", "3,14", "6,2", "6,6", "6,8", "6,12", "7,3",
  "7,11", "8,2", "8,6", "8,8", "8,12", "11,0", "11,7", "11,14", "12,6", "12,8", "14,3", "14,11",
])

export function premiumType(row: number, col: number): PremiumType {
  if (row === 7 && col === 7) return "center"
  const key = `${row},${col}`
  if (TW.has(key)) return "TW"
  if (DW.has(key)) return "DW"
  if (TL.has(key)) return "TL"
  if (DL.has(key)) return "DL"
  return "normal"
}

export function premiumLabel(type: PremiumType): string {
  switch (type) {
    case "center":
      return "★"
    case "TW":
      return "TW"
    case "DW":
      return "DW"
    case "TL":
      return "TL"
    case "DL":
      return "DL"
    default:
      return ""
  }
}

export function premiumClasses(type: PremiumType): string {
  switch (type) {
    case "center":
      return "bg-gradient-to-br from-pink-400 to-red-500 text-white"
    case "TW":
      return "bg-gradient-to-br from-red-500 to-red-600 text-white"
    case "DW":
      return "bg-gradient-to-br from-pink-400 to-pink-500 text-white"
    case "TL":
      return "bg-gradient-to-br from-blue-500 to-blue-600 text-white"
    case "DL":
      return "bg-gradient-to-br from-cyan-400 to-cyan-500 text-white"
    default:
      return "bg-green-50 text-gray-600"
  }
}

/** Human-friendly square name, e.g. (7,7) -> "H8". */
export function cellLabel(row: number, col: number): string {
  return `${String.fromCharCode(65 + col)}${row + 1}`
}

export function emptyBoard(): (BoardCell | null)[][] {
  return Array.from({ length: BOARD_SIZE }, () =>
    Array.from({ length: BOARD_SIZE }, () => null as BoardCell | null),
  )
}
