# Magic 8 Ball — How It Works

A simple command-line Magic 8 Ball built for a work demo on basic Python concepts: lists, functions, loops, exception handling, and user input.

## Running it

```
python magic8ball.py
```

Type a yes/no question and press Enter. Type `quit` or `exit` to leave the program.

## Walkthrough

### 1. The response pool

```python
RESPONSES = [
    "It is certain.",
    "Reply hazy, try again.",
    "Don't count on it.",
    ...
]
```

A list of the 20 classic Magic 8 Ball answers, grouped loosely into affirmative, non-committal, and negative responses (the grouping is just for readability — the list is flat).

### 2. The `ask` function

```python
def ask(question):
    if not question.strip():
        raise ValueError("You have to actually ask a question.")
    return random.choice(RESPONSES)
```

- `question.strip()` removes leading/trailing whitespace so a blank or whitespace-only input is treated as "no question asked".
- If there's nothing there, it raises a `ValueError` — this separates "bad input" from "normal output" and lets the caller decide how to handle it.
- Otherwise, `random.choice()` picks one item from `RESPONSES` at random and returns it.

### 3. The main loop

```python
def main():
    while True:
        question = input("Your question: ").strip()

        if question.lower() in ("quit", "exit"):
            print("Goodbye!")
            sys.exit(0)

        try:
            answer = ask(question)
        except ValueError as e:
            print(f"{e}\n")
            continue

        print(f"🎱 {answer}\n")
```

- Runs an infinite loop (`while True`) so the user can ask multiple questions without restarting the script.
- Checks for `quit`/`exit` (case-insensitive) to break out cleanly via `sys.exit(0)`.
- Wraps the call to `ask()` in a `try/except` block — if it raises `ValueError` (empty question), the error message is printed and `continue` restarts the loop without crashing.
- Otherwise, it prints the answer prefixed with a 🎱 emoji.

### 4. Entry point guard

```python
if __name__ == "__main__":
    main()
```

Ensures `main()` only runs when the script is executed directly (`python magic8ball.py`), not if it's imported as a module elsewhere — useful if you later want to reuse `ask()` in another script (e.g. a Slack bot or web app) without triggering the CLI loop.

## Possible extensions for the demo

- Swap `input()`/`print()` for a Flask/FastAPI endpoint to turn it into a web API.
- Add a `--question` CLI argument (via `argparse`) for a non-interactive, one-shot mode.
- Log each question/answer pair to a file to show basic file I/O.
- Seed `random` with a fixed value to demonstrate deterministic testing.
