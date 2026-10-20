import re

from src.utils.logger import logger


class TextCleaner:
    def __init__(self) -> None:
        pass

    @staticmethod
    def clean_data(text: str) -> str:
        if not text:
            logger.warning("Empty text provided")
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"http\S+|www\.\S+", " ", text)
        text = re.sub(r"\S+@\S+", " ", text)
        text = re.sub(r"[#*_`~>]+", " ", text)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
        text = re.sub(r"([.\-]){2,}", r"\1", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()