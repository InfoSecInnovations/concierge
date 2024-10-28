from getpass import getpass
from zxcvbn import zxcvbn


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
                score = -1
    return value
