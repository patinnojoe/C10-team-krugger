"""Memory-bounded, balanced, two-stage SuperBPE trainer."""
from __future__ import annotations
import argparse, heapq, importlib, json, re, unicodedata
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATHS = {name: PROJECT_ROOT / "data" / f"{name}.txt" for name in
                ("swahili", "igbo", "yoruba", "hausa", "zulu")}
OPTIONAL_LANGUAGES = {"zulu"}
ASCII_TOKENS = [chr(index) for index in range(128)]
PUNCTUATION = {"‘":"'","’":"'","‚":"'","‛":"'","“":'"',"”":'"',"„":'"',"‟":'"',
               "‐":"-","‑":"-","‒":"-","–":"-","—":"-","―":"-","…":"...",
               "።":".","፣":",","፤":";","፥":":","፦":":","፧":"?","፨":" "," ":" "}

def fallback_preprocess(text: str) -> str:
    """Best stdlib approximation of the published ASCII preprocessing contract."""
    text = unicodedata.normalize("NFKC", text)
    pieces = []
    for char in text:
        if char in PUNCTUATION:
            pieces.append(PUNCTUATION[char])
        elif ord(char) < 128:
            pieces.append(char)
        else:
            ascii_hint = "".join(c for c in unicodedata.normalize("NFKD", char)
                                 if ord(c) < 128 and c.isprintable())
            if ascii_hint:
                pieces.append(ascii_hint)
            pieces.append(f"[U+{ord(char):04X} {unicodedata.name(char, 'UNKNOWN CHARACTER')}]")
    return re.sub(r"\s+", " ", "".join(pieces)).strip()

def resolve_preprocessor(specification: Optional[str]) -> tuple[Callable[[str], str], str]:
    if not specification:
        print("WARNING: using fallback preprocessing (official file unavailable)")
        return fallback_preprocess, "fallback-ascii-v2"
    try:
        module_name, function_name = specification.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
    except (ValueError, ImportError, AttributeError) as error:
        raise ValueError("--preprocessor must be an importable module:function") from error
    return function, specification

def _read_windows(path: Path, approximate_raw_chars: int, windows: int = 12) -> str:
    """Read bounded, evenly distributed windows from a potentially huge file."""
    size = path.stat().st_size
    budget = max(64_000, approximate_raw_chars * 2)
    if size <= budget:
        return path.read_text(encoding="utf-8", errors="replace")
    width = max(8_192, budget // windows)
    chunks = []
    with path.open("rb") as handle:
        for number in range(windows):
            offset = ((size - width) * number) // max(1, windows - 1)
            handle.seek(offset)
            chunks.append(handle.read(width).decode("utf-8", errors="replace"))
    return "\n".join(chunks)

def _split_sample(processed: str, wanted: int) -> tuple[str, str]:
    validation_size = min(max(10_000, wanted // 5), max(1, len(processed) // 5))
    if len(processed) <= validation_size + 1:
        raise ValueError("corpus is too small for disjoint train and validation data")
    validation, pool = processed[-validation_size:], processed[:-validation_size]
    if len(pool) <= wanted:
        return pool, validation
    parts, width, selected = 8, max(1, wanted // 8), []
    for index in range(parts):
        start = ((len(pool) - width) * index) // (parts - 1)
        selected.append(pool[start:start + width])
    return " ".join(selected)[:wanted], validation

def load_balanced_corpora(chars_per_language: int, preprocessor: Callable[[str], str]):
    training, validation = {}, {}
    for language, path in CORPUS_PATHS.items():
        if not path.is_file():
            if language in OPTIONAL_LANGUAGES:
                print(f"{language}: optional corpus absent; continuing")
                continue
            raise FileNotFoundError(f"missing {language} corpus: {path}")
        raw = _read_windows(path, chars_per_language + max(10_000, chars_per_language // 5))
        processed = preprocessor(raw)
        if not processed:
            if language in OPTIONAL_LANGUAGES:
                print(f"{language}: optional corpus empty; continuing")
                continue
            raise ValueError(f"{language} corpus is empty after preprocessing")
        if not processed.isascii():
            raise ValueError(f"preprocessor output for {language} is not ASCII")
        train, held_out = _split_sample(processed, chars_per_language)
        training[language], validation[language] = train, held_out
        print(f"{language:10} file_bytes={path.stat().st_size:,} sampled_raw={len(raw):,} "
              f"processed={len(processed):,} train={len(train):,} validation={len(held_out):,}")
        print(f"  sample={processed[:100]!r}")
    if len(training) < 2:
        raise ValueError("at least two usable languages are required")
    common = min(map(len, training.values()))
    training = {language: text[:common] for language, text in training.items()}
    print(f"active languages: {', '.join(training)}")
    print(f"balanced characters/language: {common:,}; total: {common * len(training):,}")
    return training, validation

class IncrementalBPE:
    """Adjacent-pair BPE with incrementally maintained occurrence sets."""
    def __init__(self, texts: dict[str, str]):
        self.tokens = list(ASCII_TOKENS)
        self.token_to_id = {token: index for index, token in enumerate(self.tokens)}
        self.value, self.previous, self.following, self.alive = [], [], [], []
        self.occurrences = defaultdict(set)
        for text in texts.values():
            first = len(self.value)
            for char in text:
                index = len(self.value)
                self.value.append(ord(char)); self.previous.append(index - 1 if index > first else -1)
                self.following.append(index + 1); self.alive.append(True)
            if len(self.value) > first:
                self.following[-1] = -1
                for index in range(first, len(self.value) - 1):
                    self.occurrences[(self.value[index], self.value[index + 1])].add(index)
        self.heap = []

    def _allowed(self, pair, phase):
        return phase == 2 or (" " not in self.tokens[pair[0]] and " " not in self.tokens[pair[1]])

    def _rebuild_heap(self, phase):
        self.heap = [(-len(sites), pair[0], pair[1]) for pair, sites in self.occurrences.items()
                     if sites and self._allowed(pair, phase)]
        heapq.heapify(self.heap)

    def _best(self, phase):
        while self.heap:
            negative, left, right = heapq.heappop(self.heap)
            pair = (left, right); current = len(self.occurrences.get(pair, ()))
            if current == -negative and current and self._allowed(pair, phase):
                return pair, current
        return None, 0

    def _discard(self, pair, site, dirty):
        sites = self.occurrences.get(pair)
        if sites is not None and site in sites:
            sites.discard(site); dirty.add(pair)

    def _add(self, pair, site, dirty):
        self.occurrences[pair].add(site); dirty.add(pair)

    def merge(self, pair, new_id, phase):
        dirty, count = set(), 0
        for left in sorted(self.occurrences.get(pair, ())):
            if not self.alive[left] or self.value[left] != pair[0]:
                continue
            right = self.following[left]
            if right < 0 or not self.alive[right] or self.value[right] != pair[1]:
                continue
            before, after = self.previous[left], self.following[right]
            self._discard(pair, left, dirty)
            if before >= 0: self._discard((self.value[before], pair[0]), before, dirty)
            if after >= 0: self._discard((pair[1], self.value[after]), right, dirty)
            self.value[left] = new_id; self.following[left] = after; self.alive[right] = False
            if after >= 0: self.previous[after] = left
            if before >= 0: self._add((self.value[before], new_id), before, dirty)
            if after >= 0: self._add((new_id, self.value[after]), left, dirty)
            count += 1
        for changed in dirty:
            frequency = len(self.occurrences.get(changed, ()))
            if frequency and self._allowed(changed, phase):
                heapq.heappush(self.heap, (-frequency, changed[0], changed[1]))
        return count

    def train(self, target, transition, minimum):
        if not 128 <= transition <= target <= 20_000:
            raise ValueError("require 128 <= transition <= vocabulary <= 20000")
        merges, phase = [], 1
        self._rebuild_heap(phase)
        while len(self.tokens) < target:
            wanted_phase = 1 if len(self.tokens) < transition else 2
            if wanted_phase != phase:
                phase = wanted_phase; self._rebuild_heap(phase)
                print(f"transitioning to phase 2 at vocabulary {len(self.tokens):,}")
            pair, frequency = self._best(phase)
            if pair is None or frequency < minimum:
                print(f"stopped at vocabulary {len(self.tokens):,}; best frequency={frequency}"); break
            token = self.tokens[pair[0]] + self.tokens[pair[1]]
            new_id = self.token_to_id.get(token)
            if new_id is None:
                new_id = len(self.tokens); self.token_to_id[token] = new_id; self.tokens.append(token)
            merged = self.merge(pair, new_id, phase)
            merges.append([pair[0], pair[1], new_id])
            if len(self.tokens) % 500 == 0:
                print(f"vocab={len(self.tokens):,} phase={phase} frequency={frequency:,} merged={merged:,}")
        return self.tokens, merges

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chars-per-language", type=int, default=300_000)
    parser.add_argument("--vocab-size", type=int, default=19_000)
    parser.add_argument("--phase1-vocab-size", type=int, default=12_000)
    parser.add_argument("--min-frequency", type=int, default=2)
    parser.add_argument("--preprocessor", help="official callable as module:function")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "tokenizer.json")
    args = parser.parse_args()
    preprocessor, preprocessor_name = resolve_preprocessor(args.preprocessor)
    training, validation = load_balanced_corpora(args.chars_per_language, preprocessor)
    started = perf_counter(); trainer = IncrementalBPE(training)
    tokens, merges = trainer.train(args.vocab_size, args.phase1_vocab_size, args.min_frequency)
    cross_space = [token for token in tokens[128:] if " " in token]
    model = {"version":2,"inference":"minimum-token-trie","training_preprocessor":preprocessor_name,
             "training_languages":list(training),"balanced_chars_per_language":min(map(len, training.values())),
             "tokens":tokens,"merges":merges}
    args.output.write_text(json.dumps(model, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    validation_path = PROJECT_ROOT / "artifacts" / "validation.json"
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps(validation, ensure_ascii=True), encoding="utf-8")
    print(f"training seconds: {perf_counter()-started:.3f}")
    print(f"final vocabulary: {len(tokens):,}; cross-space tokens: {len(cross_space):,}")
    print(f"cross-space sample: {cross_space[:20]!r}")
    print(f"wrote {args.output} and {validation_path}")

if __name__ == "__main__": main()
