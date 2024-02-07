from flask import Flask, render_template, request
import itertools

app = Flask(__name__)

# load a text file containing a list of english words
with open('Collins Scrabble Words (2019).txt', 'r') as f:
    english_words = set(f.read().splitlines())

# Scrabble letter scores
scores = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8,
    'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1,
    'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

def word_score(word, zero_indices=[]):
    """
    Calculate the score of a word based on Scrabble letter scores.
    """
    return sum(scores.get(letter.upper(), 0) if i not in zero_indices else 0 for i, letter in enumerate(word))

def scrabble_word_builder(letters, board_letters):
    """
    Generate all possible words that can be formed from the given letters and board letters.
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

@app.route('/', methods=['GET', 'POST'])
def scrabble_word_builder_web():
    if request.method == 'POST':
        letters = request.form['letters']
        board_letters = request.form['board_letters']
        words_scores = scrabble_word_builder(letters, board_letters)
        words_by_length = {}
        for word, score in words_scores:
            if len(word) not in words_by_length:
                words_by_length[len(word)] = [(word, score)]
            else:
                words_by_length[len(word)].append((word, score))
        for length in words_by_length:
            words_by_length[length].sort(key=lambda x: x[0])  # Sort alphabetically
            words_by_length[length].sort(key=lambda x: x[1], reverse=True)  # Sort by score
        return render_template('result.html', words_by_length=words_by_length)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
