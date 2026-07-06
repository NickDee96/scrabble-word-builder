export interface WordResult {
  word: string
  score: number
  length: number
}

/** Tailwind badge color for a word's score, bucketed by value. */
export function getScoreColor(score: number): string {
  if (score >= 15) return "bg-red-500"
  if (score >= 10) return "bg-orange-500"
  if (score >= 7) return "bg-yellow-500"
  return "bg-green-500"
}

/** Group results by word length, preserving input order within each group. */
export function groupResultsByLength(results: WordResult[]): Record<number, WordResult[]> {
  const grouped: Record<number, WordResult[]> = {}
  for (const result of results) {
    if (!grouped[result.length]) grouped[result.length] = []
    grouped[result.length].push(result)
  }
  return grouped
}
