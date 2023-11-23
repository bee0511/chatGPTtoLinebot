import math


def Heron():
    a = float(input("Please enter the number a: "))
    b = float(input("Please enter the number b: "))
    c = float(input("Please enter the number c: "))
    s = (a + b + c) / 2
    return math.sqrt(s * (s - a) * (s - b) * (s - c))


if __name__ == "__main__":
    print("The answer is: {}".format(Heron()))
