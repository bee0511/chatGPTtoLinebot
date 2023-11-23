import random

if __name__ == "__main__":
    num_list = [i + 1 for i in range(50)]
    ans = random.sample(num_list, 1)[0]
    while True:
        guess = int(input("Please enter your guess: "))
        if guess > ans:
            print("Lower! Try again.")
        elif guess < ans:
            print("Higher! Try again.")
        else:
            print("You got it!!!")
            break
