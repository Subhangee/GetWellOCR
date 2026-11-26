# Test cases (all fictional)

One patient, Helga Beispiel (78, shortness of breath), in three difficulty steps.
Every set has a ground-truth file, so every run gives a score.

```
data/cases/
├── case01/                       BASE CASE: 20 pages, printed documents
│   ├── case01_all.pdf            all pages, to print or view
│   ├── pages_clean/              perfect scans (PNG)
│   ├── pages_photo/              realistic phone photos (JPG)   <- default demo input
│   ├── stress/                   SET A: the same pages, damaged on purpose (not in git, re-create)
│   │   ├── manifest.json         what every image is: type, level, setting, source page
│   │   ├── blur/L1 … L4/         out of focus
│   │   ├── noise/L1 … L4/        dark room, sensor noise
│   │   ├── skew/L1 … L4/         crooked photo (up to 15°)
│   │   ├── shadow/L1 … L4/       hand or phone shadow, one-sided light
│   │   ├── jpeg/L1 … L4/         sent through WhatsApp / e-mail
│   │   └── fax/L1 … L4/          low resolution, black/white only
│   ├── case01_answers.json       ground truth: documents, medication, 5 conflicts, 13 critical facts, traps
│   └── case01_mock_api.json      response format for the frontend
│
└── case01_hard/                  SET B: same patient, harder DOCUMENTS
    ├── case01_hard_all.pdf
    ├── pages_clean/  pages_photo/
    ├── manifest.json             what was changed on which page
    └── case01_hard_answers.json  ground truth: 14 critical facts, 6 conflicts
```

Levels: L1 = mild, L2 = typical bad photo, L3 = hard, L4 = almost unreadable.

## What is different in case01_hard

| Page | Change | Tests | Changes the truth? |
|---|---|---|---|
| 1 | Underline and "!!" by hand | Pen marks don't break reading | no |
| 3 | Glimepirid row struck through, "abgesetzt 20.11." | Strike-through = stopped | no (confirms the fax) |
| 4 | Medication plan in landscape, photographed sideways, "ALT!" written on it | Page orientation | no |
| 6 | Cumulative lab table turned on its side (dates = rows) | Horizontal tables | no |
| 7 | Side note "Ramipril pausiert seit 20.11. (Schwindel)" | Handwritten facts | **yes: new fact N14, conflict C6** |
| 9 | Table without grid lines | Tables aligned only by spacing | no |
| 13 | Signature scribble | Noise | no |
| 14 | "keine bekannt" struck through, "Penicillin!" written next to it | Handwritten corrections | **yes: conflict C5 changes** |

## Commands

```powershell
python scripts\generate_case.py                    # case01 (already in git)
python scripts\make_hard_case.py                   # case01_hard
python scripts\make_stress_set.py                  # set A for case01 (~230 MB, not in git)
python scripts\make_stress_set.py --case case01_hard

python scripts\process_case.py                                            # one case, with scorecard
python scripts\process_case.py --pages data\cases\case01_hard\pages_photo
python scripts\run_stress.py                       # all damage types and levels -> chart + CSV
python scripts\run_stress.py --quick               # levels 2 and 4 only
```

## Still to add by the team

- **Real bad photos**: print `case01_all.pdf`, photograph it badly (dim light, angle, thumb in frame,
  crumpled, plastic sleeve), put the photos in `data/cases/case01_real/pages_photo/`,
  copy `case01_answers.json` as `case01_real_answers.json`, run `process_case.py --pages …`.
- **Real handwriting**: ask the doctor to write on printed pages the way doctors do
  (strike-throughs, side notes). Record every change in the answers file, like case01_hard.
