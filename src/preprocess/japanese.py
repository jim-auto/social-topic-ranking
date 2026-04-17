from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
NOISE_PATTERN = re.compile(r"[\[\]{}()（）「」『』【】!！?？,，.。:：;；/／\\|｜#＃]")
TOKEN_PATTERN = re.compile(r"[0-9A-Za-zぁ-んァ-ヶ一-龠ー]+")


class JapaneseTextPreprocessor:
    def __init__(self, stopwords: list[str] | None = None) -> None:
        self.stopwords = {self.normalize_text(word) for word in (stopwords or [])}
        self._sudachi_tokenizer: Any | None = None
        self._sudachi_mode: Any | None = None
        self._fugashi_tagger: Any | None = None
        self._tokenizer_name = "regex"

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "JapaneseTextPreprocessor":
        stopwords = settings.get("preprocess", {}).get("stopwords", [])
        return cls(stopwords=stopwords)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        required = {"keyword", "score"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Input data is missing required columns: {sorted(missing)}")

        df = frame.copy()
        if "date" not in df.columns:
            df["date"] = pd.Timestamp.today().date().isoformat()
        if "source" not in df.columns:
            df["source"] = "input"

        df["keyword"] = df["keyword"].astype(str)
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
        df["normalized_keyword"] = df["keyword"].map(self.normalize_text)
        df["nouns"] = df["normalized_keyword"].map(lambda value: "|".join(self.extract_nouns(value)))
        df["tokenizer"] = self._tokenizer_name
        return df

    def normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(text)).lower().strip()
        normalized = URL_PATTERN.sub(" ", normalized)
        normalized = NOISE_PATTERN.sub(" ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def extract_nouns(self, text: str) -> list[str]:
        for extractor in (self._extract_with_sudachi, self._extract_with_fugashi):
            tokens = extractor(text)
            if tokens:
                return self._remove_stopwords(tokens)
        tokens = TOKEN_PATTERN.findall(text)
        return self._remove_stopwords(tokens)

    def _remove_stopwords(self, tokens: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            token = self.normalize_text(token)
            if not token or token in self.stopwords or token in seen:
                continue
            cleaned.append(token)
            seen.add(token)
        return cleaned

    def _extract_with_sudachi(self, text: str) -> list[str]:
        try:
            if self._sudachi_tokenizer is None:
                from sudachipy import dictionary
                from sudachipy import tokenizer as sudachi_tokenizer

                self._sudachi_tokenizer = dictionary.Dictionary().create()
                self._sudachi_mode = sudachi_tokenizer.Tokenizer.SplitMode.C
            tokens = []
            for morpheme in self._sudachi_tokenizer.tokenize(text, self._sudachi_mode):
                pos = morpheme.part_of_speech()
                if pos and pos[0] == "名詞":
                    tokens.append(morpheme.normalized_form())
            if tokens:
                self._tokenizer_name = "sudachi"
            return tokens
        except Exception:
            return []

    def _extract_with_fugashi(self, text: str) -> list[str]:
        try:
            if self._fugashi_tagger is None:
                from fugashi import Tagger

                self._fugashi_tagger = Tagger()
            tokens = []
            for word in self._fugashi_tagger(text):
                feature = getattr(word, "feature", None)
                pos = getattr(feature, "pos1", None)
                if pos is None and isinstance(feature, tuple) and feature:
                    pos = feature[0]
                if pos == "名詞":
                    tokens.append(str(word.surface))
            if tokens:
                self._tokenizer_name = "fugashi"
            return tokens
        except Exception:
            return []
