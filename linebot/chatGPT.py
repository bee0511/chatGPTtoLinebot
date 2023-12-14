import openai
from mylinebot.secret import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

history = []


def chat(message):
    history.append({"role": "user", "content": message + " 請用繁體中文回答"})
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}]
    )
    response_message = response.choices[0].message
    history.append({"role": response_message.role, "content": response_message.content})

    return response_message.content


if __name__ == "__main__":
    while True:
        input_message = input("What can I help you? ")
        response_message = chat(input_message)
        print(response_message)
