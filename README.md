# Scrabble Word Builder

This project is a Scrabble Word Builder, a Python script that generates all possible words that can be formed from a given set of letters and board letters. It was authored by Nick Mumero, a Machine Learning Engineer, as a solver for his favorite puzzle game.

## File Structure

The project consists of two main files:

```
scrabble/
┣ Collins Scrabble Words (2019).txt
┗ scrabble.py
```

- `Collins Scrabble Words (2019).txt`: This text file contains a list of English words that the script uses to generate possible words.
- `scrabble.py`: This is the main Python script that generates the possible words.

## Usage

To use the script, you need to pass the letters you want to use to form words as a command line argument. You can also optionally pass the letters on the board to use to form words.

Here's an example of how to run the script:

```bash
python scrabble.py --letters "wertash" --board_letters "bak"
```

In this example, the script will generate all possible words that can be formed from the letters "wertash" and the board letters "bak".

## Logic Explanation

The script uses the itertools.permutations function to generate all possible permutations of the given letters for lengths from 1 to the length of the input letters. For each permutation, it checks if the word is in the list of English words. If it is, it calculates the score of the word based on Scrabble letter scores and adds it to the list of possible words.

The time complexity of this script is O(n!) where n is the number of input letters. This is because it generates all permutations of the input letters. The space complexity is also O(n!) because it stores all possible words in a list.

## Further Todos

- **Web Interface**: Implement a web interface for the script using a framework like Flask or Django. This would make the script more user-friendly and accessible to non-technical users.
- **Speed Up Logic**: The current logic of generating all permutations of the input letters can be slow for large inputs. Consider using a more efficient algorithm or data structure to speed up the script. For example, you could use a Trie data structure to store the English words and quickly check if a word is valid.
- **Parallel Processing**: Consider using parallel processing to speed up the generation of permutations and the checking of words. This could significantly reduce the runtime of the script for large inputs.

## Author

This project was authored by Nick Mumero, a Machine Learning Engineer. You can find him on GitHub under the username [NickDee96](https://github.com/NickDee96).

## License

This project is open source, feel free to use, modify and distribute it.