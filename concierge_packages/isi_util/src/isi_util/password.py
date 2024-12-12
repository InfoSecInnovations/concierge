from getpass import getpass
from zxcvbn import zxcvbn
import secrets


def get_strong_password(prompt):
    score = -1
    while score < 4:
        value = getpass(prompt)
        strength = zxcvbn(value)
        score = strength["score"]
        if strength["score"] < 4:
            print("Password does not meet the strength requirements")
            print(*strength["feedback"]["suggestions"], sep="\n")
        else:
            confirm = getpass("Confirm password: ")
            if value != confirm:
                print("passwords didn't match, please enter again!")
                score = -1
    return value


def generate_strong_password():
    score = -1
    while score < 4:
        value = secrets.token_hex(25)
        strength = zxcvbn(value)
        score = strength["score"]
    return value
