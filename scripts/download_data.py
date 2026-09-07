"""Download the four supplied training corpora from Google Drive."""

from pathlib import Path

import gdown


ROOT = Path(__file__).resolve().parent.parent
DATASETS = {
    "igbo.txt": "1Qp0eOBqy35u_KX-EU3uD7Fozfyjsj0Zf",
    "yoruba.txt": "1rnD_lv70MOrLpHd7rTrZ3Df7GfDYXDCT",
    "swahili.txt": "1DWdsB4zo6CErU9-2mpxVJjKs8mA7xZyz",
    "hausa.txt": "17lTY7Nqtwg21XctG_T7De8DBPsuR1U1J",
}


def main() -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename, file_id in DATASETS.items():
        destination = data_dir / filename
        if destination.is_file() and destination.stat().st_size:
            print(f"exists, skipping: {destination}")
            continue
        print(f"downloading: {filename}")
        result = gdown.download(id=file_id, output=str(destination), quiet=False)
        if result is None or not destination.is_file() or not destination.stat().st_size:
            raise RuntimeError(f"download failed: {filename}")
    print("All required corpora are available.")


if __name__ == "__main__":
    main()
