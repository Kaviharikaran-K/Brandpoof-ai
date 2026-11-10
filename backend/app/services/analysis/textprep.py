import re
import unicodedata


def normalise(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00a0", " ").replace("\t", "    ")
    lines = [re.sub(r"[ ]+$", "", line) for line in text.split("\n")]
    return "\n".join(lines)
