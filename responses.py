from random import choice, randint

def get_response(user_input: str) -> str:
    lowered: str = user_input.lower()
    if lowered == "":
        return "Bitch... I need a command"
    elif "start" in lowered:
        return "Starting Facetime call..."
    elif "end" in lowered:
        return "Disconnecting From FaceTime...\nGoodbye !"

