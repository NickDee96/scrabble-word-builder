import argparse

from scrabble_engine import scrabble_word_builder


def main():
    parser = argparse.ArgumentParser(description='Scrabble Word Builder')
    parser.add_argument('--letters', type=str, required=True, help='Letters to use to form words')
    parser.add_argument('--board_letters', type=str, default="", help='Letters on the board to use to form words')
    args = parser.parse_args()

    words_scores = scrabble_word_builder([x for x in args.letters], [x for x in args.board_letters])
    
    # Group words by length
    words_by_length = {}
    for word, score in words_scores:
        if len(word) not in words_by_length:
            words_by_length[len(word)] = [(word, score)]
        else:
            words_by_length[len(word)].append((word, score))
    
    # Sort each group by score and then alphabetically
    for length in words_by_length:
        words_by_length[length].sort(key=lambda x: x[0])  # Sort alphabetically
        words_by_length[length].sort(key=lambda x: x[1], reverse=True)  # Sort by score
    
    # Print out the words
    for length in sorted(words_by_length.keys()):
        print(f"{length}-Letter Words:")
        for word, score in words_by_length[length]:
            print(f"Word: {word}, Score: {score}")
        print()

if __name__ == "__main__":
    main()
