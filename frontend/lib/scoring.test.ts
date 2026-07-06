import { describe, expect, it } from "vitest"

import { getScoreColor, groupResultsByLength, type WordResult } from "./scoring"

describe("getScoreColor", () => {
  it("maps score ranges to badge colors", () => {
    expect(getScoreColor(20)).toBe("bg-red-500")
    expect(getScoreColor(15)).toBe("bg-red-500")
    expect(getScoreColor(12)).toBe("bg-orange-500")
    expect(getScoreColor(10)).toBe("bg-orange-500")
    expect(getScoreColor(8)).toBe("bg-yellow-500")
    expect(getScoreColor(7)).toBe("bg-yellow-500")
    expect(getScoreColor(5)).toBe("bg-green-500")
    expect(getScoreColor(0)).toBe("bg-green-500")
  })
})

describe("groupResultsByLength", () => {
  it("groups results by word length, preserving order", () => {
    const results: WordResult[] = [
      { word: "CAT", score: 5, length: 3 },
      { word: "AT", score: 2, length: 2 },
      { word: "ACT", score: 5, length: 3 },
    ]
    const grouped = groupResultsByLength(results)
    expect(Object.keys(grouped).sort()).toEqual(["2", "3"])
    expect(grouped[3].map((r) => r.word)).toEqual(["CAT", "ACT"])
    expect(grouped[2]).toHaveLength(1)
  })

  it("returns an empty object for no results", () => {
    expect(groupResultsByLength([])).toEqual({})
  })
})
