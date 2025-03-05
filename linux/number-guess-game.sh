#!/bin/bash

# Generate a random number between 1 and 100
TARGET=$((RANDOM % 100 + 1))

# Initialize guess count
GUESSES=0

echo "Welcome to the Number Guessing Game!"
echo "Try to guess the number between 1 and 100."

while true; do
    # Prompt user for input
    read -p "Enter your guess: " GUESS
    ((GUESSES++))
    
    # Check if input is a number
    if ! [[ "$GUESS" =~ ^[0-9]+$ ]]; then
        echo "Please enter a valid number."
        continue
    fi
    
    # Convert input to an integer
    GUESS=$((GUESS))
    
    # Compare guess with target number
    if (( GUESS < TARGET )); then
        echo "Too low! Try again."
    elif (( GUESS > TARGET )); then
        echo "Too high! Try again."
    else
        echo "Congratulations! You guessed the number in $GUESSES attempts."
        break
    fi
done
