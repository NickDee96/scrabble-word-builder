import itertools
import argparse
from typing import List, Tuple

# load a text file containing a list of english words
with open('Collins Scrabble Words (2019).txt', 'r') as f:
    english_words = set(f.read().splitlines())

# Scrabble letter scores
scores = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8,
    'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1,
    'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

def word_score(word: str, zero_indices: List[int] = []) -> int:
    """
    Calculate the score of a word based on Scrabble letter scores.

    Args:
        word (str): The word to calculate the score for.
        zero_indices (List[int]): Indices in the word that should be scored as zero.

    Returns:
        int: The score of the word.
    """
    return sum(scores.get(letter.upper(), 0) if i not in zero_indices else 0 for i, letter in enumerate(word))

def scrabble_word_builder(letters: List[str], board_letters: List[str]) -> List[Tuple[str, int]]:
    """
    Generate all possible words that can be formed from the given letters and board letters.

    Args:
        letters (List[str]): The letters to use to form words.
        board_letters (List[str]): The letters on the board to use to form words.

    Returns:
        List[Tuple[str, int]]: A list of possible words and their scores.
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

def main():
    parser = argparse.ArgumentParser(description='Scrabble Word Builder')
    parser.add_argument('--letters', type=str, required=True, help='Letters to use to form words')
    parser.add_argument('--board_letters', type=str, default="", help='Letters on the board to use to form words')
    args = parser.parse_args()

    for word, score in scrabble_word_builder([x for x in args.letters], [x for x in args.board_letters]):
        print(f"Word: {word}, Score: {score}")

if __name__ == "__main__":
    main()