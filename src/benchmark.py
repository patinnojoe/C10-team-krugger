import argparse, json, sys
from pathlib import Path
from time import perf_counter
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from tokenizer import Tokenizer

def measure(label, texts):
    characters = sum(map(len, texts)); start = perf_counter(); encoder = Tokenizer(); init1 = perf_counter()-start
    start = perf_counter(); encoded = encoder.encode(texts); encoding = perf_counter()-start
    start = perf_counter(); decoder = Tokenizer(); init2 = perf_counter()-start
    start = perf_counter(); decoded = decoder.decode(encoded); decoding = perf_counter()-start
    assert decoded == texts and all(type(x) is int for row in encoded for x in row)
    count = sum(map(len, encoded))
    print(f"{label:12} chars={characters:9,d} tokens={count:9,d} chars/token={characters/max(1,count):6.3f} "
          f"init={init1+init2:7.3f}s encode={encoding:7.3f}s decode={decoding:7.3f}s total={init1+init2+encoding+decoding:7.3f}s")

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--validation",type=Path,default=PROJECT_ROOT / "artifacts" / "validation.json"); args=parser.parse_args()
    data=json.loads(args.validation.read_text(encoding="utf-8"))
    for language,text in data.items(): measure(language,[text])
    measure("combined",list(data.values()))
if __name__ == "__main__": main()
