def calculate_bmi(w, h):
    return w / (h**2)

w = float(input("Please enter your weight(kg): "))
h = float(input("Please enter your height(m): "))

print("Your BMI is:", calculate_bmi(w, h))
