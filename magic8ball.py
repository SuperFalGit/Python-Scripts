import random
import sys

RESPONSES = [
    # Affirmative
    "It is certain.",
    "It is decidedly so.",
    "Without a doubt.",
    "Yes, definitely.",
    "You may rely on it.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    # Non-committal
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    # Negative
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
]


def ask(question):
    if not question.strip():
        raise ValueError("You have to actually ask a question.")
    return random.choice(RESPONSES)


def main():
    print("Magic 8 Ball - ask a yes/no question. Type 'quit' to exit.\n")

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

        print(f"\U0001F3B1 {answer}\n")


if __name__ == "__main__":
    main()
