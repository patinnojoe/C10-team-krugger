"""Standalone competition-time tokenizer; Python standard library only."""
from __future__ import annotations
import json
from array import array
from pathlib import Path

class Tokenizer:
    def __init__(self):
        with Path(__file__).with_name("tokenizer.json").open("r", encoding="utf-8") as handle:
            model = json.load(handle)
        tokens = model.get("tokens")
        if not isinstance(tokens, list) or not tokens or len(tokens) > 20_000:
            raise ValueError("invalid tokenizer vocabulary")
        if len(tokens) != len(set(tokens)):
            raise ValueError("tokenizer vocabulary contains duplicates")
        self._tokens = tokens
        self._trie = {}
        for token_id, token in enumerate(tokens):
            if not isinstance(token, str) or not token:
                raise ValueError("vocabulary tokens must be non-empty strings")
            node = self._trie
            for character in token:
                node = node.setdefault(character, {})
            node[""] = token_id

    def _encode_one(self, text):
        length = len(text)
        if not length: return []
        unreachable = length + 1
        costs = array("I", [unreachable]) * (length + 1)
        previous = array("I", [0]) * (length + 1)
        chosen = array("I", [0]) * (length + 1)
        costs[0] = 0
        for start in range(length):
            node, end, next_cost = self._trie, start, costs[start] + 1
            while end < length:
                node = node.get(text[end])
                if node is None: break
                end += 1
                token_id = node.get("")
                if token_id is not None and next_cost < costs[end]:
                    costs[end] = next_cost; previous[end] = start; chosen[end] = token_id
        if costs[length] == unreachable:
            raise ValueError("input contains a symbol missing from the base vocabulary")
        output, position = [], length
        while position:
            output.append(int(chosen[position])); position = previous[position]
        output.reverse(); return output

    def encode(self, texts: list[str]) -> list[list[int]]:
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise TypeError("encode expects list[str]")
        return [self._encode_one(text) for text in texts]

    def decode(self, encoded_texts: list[list[int]]) -> list[str]:
        if not isinstance(encoded_texts, list): raise TypeError("decode expects list[list[int]]")
        decoded = []
        for row in encoded_texts:
            if not isinstance(row, list): raise TypeError("decode expects list[list[int]]")
            pieces = []
            for token_id in row:
                if type(token_id) is not int: raise TypeError("token IDs must be plain Python int values")
                if token_id < 0 or token_id >= len(self._tokens): raise ValueError(f"invalid token ID: {token_id}")
                pieces.append(self._tokens[token_id])
            decoded.append("".join(pieces))
        return decoded
