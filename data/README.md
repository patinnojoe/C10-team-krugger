# Dataset setup

The raw corpora are excluded from Git because their combined size is
approximately 265 MB and one file exceeds GitHub's 100 MB limit.

Run `python3 scripts/download_data.py`, or download the files manually from the
links below and save them using these exact names:

```text
data/swahili.txt
data/igbo.txt
data/yoruba.txt
data/hausa.txt
data/zulu.txt       # optional
```

| Language | Dataset source | Team-provided file | Local filename |
|---|---|---|---|
| Swahili | [Mendeley Data](https://data.mendeley.com/datasets/d4yhn5b9n6/2) | [Google Drive](https://drive.google.com/file/d/1DWdsB4zo6CErU9-2mpxVJjKs8mA7xZyz/view?usp=drive_link) | `swahili.txt` |
| Hausa | [Hugging Face](https://huggingface.co/datasets/0xnu/hausa) | [Google Drive](https://drive.google.com/file/d/17lTY7Nqtwg21XctG_T7De8DBPsuR1U1J/view?usp=sharing) | `hausa.txt` |
| Igbo | Original source not recorded | [Google Drive](https://drive.google.com/file/d/1Qp0eOBqy35u_KX-EU3uD7Fozfyjsj0Zf/view?usp=drivesdk) | `igbo.txt` |
| Yoruba | Original source not recorded | [Google Drive](https://drive.google.com/file/d/1rnD_lv70MOrLpHd7rTrZ3Df7GfDYXDCT/view) | `yoruba.txt` |
| Zulu (optional) | Not available | Not available | `zulu.txt` |

The download script stores the team-provided copies locally. `.gitignore`
prevents the large text files from being committed accidentally.
