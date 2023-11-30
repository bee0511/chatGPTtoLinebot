import math


def Heron(a, b, c):
    s = (a + b + c) / 2
    return math.sqrt(s * (s - a) * (s - b) * (s - c))


if __name__ == "__main__":
    a = float(input("Please enter the number a: "))
    b = float(input("Please enter the number b: "))
    c = float(input("Please enter the number c: "))
    print("The answer is: {}".format(Heron(a, b, c)))
