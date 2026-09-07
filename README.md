# SuperBPE for African-Language Tokenization

This repository contains our submission to the **Build a SuperBPE Tokenizer**
challenge. The tokenizer learns ordinary subword units first, then removes the
whitespace restriction so later tokens can represent frequent multi-word
expressions. It is lossless, supports ASCII symbols, uses fewer than 20,000
token IDs, and runs without network access.

## Results

| Metric                                   |        Result |
| ---------------------------------------- | ------------: |
| Total encoded tokens (50,000 characters) |        20,715 |
| CodaBench runtime                        |  0.18 seconds |
| Vocabulary size                          |        19,000 |
| Learned cross-space tokens               |        12,345 |
| Local held-out characters/token          |         6.829 |
| Local 2,000,000-character runtime        | 1.475 seconds |

## Dataset

Training used four African-language text corpora: **Swahili, Igbo, Yoruba, and
Hausa**. Zulu is supported as an optional fifth corpus but was unavailable for
the reported model. To stop the much larger Swahili and Hausa files from
dominating, the pipeline samples bounded windows across each file and truncates
all active languages to the smallest available postprocessed training size. The
reported run used 208,424 characters per language (833,696 total).

The corpora are not committed because the combined files are about 265 MB,
Swahili exceeds GitHub's per-file limit, and redistribution rights must be
confirmed. See [`data/README.md`](data/README.md).

## Training Pipeline

1. Read bounded windows distributed across each corpus instead of loading a
   large file into an expanded in-memory representation.
2. Apply NFKC normalization, simplify common punctuation, convert whitespace
   runs to one space, add readable ASCII transliterations when available, and
   emit explicit `[U+.... NAME]` markers for non-ASCII symbols.
3. Create disjoint training and validation portions, then balance languages by
   postprocessed character count.
4. Initialize the vocabulary with ASCII code points 0–127.
5. Phase 1 performs frequent adjacent-pair merges while rejecting pairs that
   contain spaces. Phase 2 continues from the learned vocabulary with space
   merges enabled.
6. Save the vocabulary and merge history in `tokenizer.json`.

Training uses incremental occurrence sets and a lazy priority queue, avoiding a
complete corpus rescan after every merge. The final configuration used a 19,000
token target, transition point 5,000, and minimum pair frequency 2. The runtime
encoder uses trie-based dynamic programming to find a minimum-token
segmentation from the learned vocabulary. Decoding concatenates token strings.

The organisers' reference preprocessing file was unavailable. The included
fallback follows the published preprocessing contract but cannot guarantee
byte-for-byte equivalence. If obtained later, pass its callable using
`--preprocessor module:function`.

## Evaluation

`tests/test_tokenizer.py` verifies:

- encoding with one instance and decoding with a fresh instance;
- exact reconstruction of empty strings, spaces, punctuation, markers, tabs,
  newlines, repetitive input, and ASCII code points 0–127;
- plain Python `int` IDs, the 20,000-token limit, and invalid-ID errors.

`src/benchmark.py` measures encoder initialization, encoding, fresh decoder
initialization, decoding, token count, characters per token, and exact
round-trip by language and combined. The packaged ZIP was also extracted and
tested independently before CodaBench upload.

## Repository Structure

```text
.
├── README.md
├── tokenizer.py              # exact CodaBench runtime code
├── tokenizer.json            # final learned model
├── src/
│   ├── train_tokenizer.py
│   └── benchmark.py
├── tests/
│   └── test_tokenizer.py
├── data/
│   └── README.md
├── docs/
├── notebooks/
│   └── README.md
├── artifacts/                # validation output and submission ZIP (ignored)
└── requirements.txt
```

## Reproduction

Python 3.12 is recommended. Runtime and training use only the standard library.

```bash
git clone https://github.com/patinnojoe/C10-team-krugger.git
cd C10-team-krugger

# Place the corpora as documented in data/README.md, then train:
python3 src/train_tokenizer.py \
  --chars-per-language 300000 \
  --vocab-size 19000 \
  --phase1-vocab-size 5000 \
  --min-frequency 2 \
  --output tokenizer.json

python3 -m unittest discover -s tests -v
python3 src/benchmark.py
zip -j artifacts/submission.zip tokenizer.py tokenizer.json
unzip -l artifacts/submission.zip
```

The CodaBench ZIP root must contain only `tokenizer.py` and `tokenizer.json`.

## Appendix: People

- **Team:** Team Kruger
- **Contributors:**  
  1.⁠ ⁠Innocent Josiah Patrick (innocentjosiahpatrick@yahoo.com)
  2.⁠ ⁠Raphael Owie Peter (raphelowie76@gmail.com)
  3.⁠ ⁠Sobowale Taofeeq Oladipupo (sobowaleayomide137@gmail.com)
  4.⁠ ⁠⁠Lawal Taofeek (techforme247@gmail.com)

5. Okundia Emmanuel (okundiaemmanuel756@gmail.com )

- **Mentor(s):** Elinah Moyo
- **Programme:** AI Saturdays Lagos, Cohort 10.

## References

1. Liu, A. et al. _SuperBPE: Space Travel for Language Models_. 2025.
2. AI Saturdays Lagos Cohort 10 project requirements.
3. CodaBench Build a SuperBPE Tokenizer competition.
