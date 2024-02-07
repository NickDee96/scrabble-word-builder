import tkinter as tk

# Create the main window
root = tk.Tk()

# Define a 15x15 grid of scores
scores = [[1 for _ in range(15)] for _ in range(15)]

# Create a 15x15 grid of buttons
for i in range(15):
    for j in range(15):
        # Set the background color based on the score
        color = "white" if scores[i][j] == 1 else "lightblue"
        
        # Create the button with the score as the text and the color as the background
        button = tk.Button(root, text=str(scores[i][j]), width=2, height=1, bg=color, fg="black")
        button.grid(row=i, column=j)

# Run the main loop
root.mainloop()
