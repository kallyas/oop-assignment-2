# OOP with Python – Assignment 2 (Advent 2026)

- **Student:** Tumuhirwe Iden
- **Student number:** S26M25/011
- **Email:** B41459@students.ucu.ac.ug

This repository has two mini-projects:

| Notebook | Mini-project | Reusable code |
|---|---|---|
| `project1_weather.ipynb` | 1. Get and show a weather forecast with web APIs (Open-Meteo, MET Norway) | `src/weather/` |
| `project2_uganda_tax.ipynb` | 2. Uganda tax engine (PAYE, NSSF, LST, VAT, corporate tax, extension A) | `src/uganda_tax/` |

## Repository structure

```
.
├── project1_weather.ipynb
├── project2_uganda_tax.ipynb
├── src/
│   ├── weather/        # HTTP client, geocoding, forecast, MET Norway, charts
│   └── uganda_tax/     # Money, Tax base class, schedules, taxes, payroll
├── tests/
│   ├── data/           # saved JSON responses for offline tests
│   └── test_*.py       # pytest and Hypothesis tests
├── requirements.txt
└── pyproject.toml      # settings for pytest and mypy
```

## Setup

You need Python 3.10 or newer.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Mini-project 1 sends your contact email in the `User-Agent` header, as the MET Norway terms require. Do not write the email in the code. Set it in an environment variable:

```bash
export WEATHER_CONTACT_EMAIL="your.name@your-university.ac.ug"
```

If you do not set it, the notebook uses the placeholder `CHANGE-ME@university.example`.

## How to run

1. Start Jupyter from the repository root: `jupyter notebook` (or `jupyter lab`).
2. Open a notebook and use **Kernel → Restart & Run All**. Both notebooks run from top to bottom with no errors.
3. In `project1_weather.ipynb`, the only cell to edit is **Configuration** (place name, candidate number, number of days, email).

Mini-project 1 needs an internet connection. Mini-project 2 works offline.

To run the notebooks from the command line:

```bash
jupyter nbconvert --to notebook --execute --inplace project1_weather.ipynb project2_uganda_tax.ipynb
```

## Tests and type checks

```bash
pytest          # 75 tests; they all run offline
mypy            # strict type check of src/ and tests/
```

- Weather tests use the saved JSON files in `tests/data/` and a mock HTTP session. They do not use the network.
- Tax tests check every PAYE band edge (335,000; 335,001; 410,000; 485,000; 10,000,000; 10,000,001).
- Hypothesis property tests check that tax is non-negative, monotonic in income, and never more than income.
- Random values use fixed seeds: `np.random.default_rng(2026)` in the notebook and `derandomize=True` for Hypothesis.

## Continuous integration (GitHub Actions)

The workflow `.github/workflows/tests.yml` runs on each push to `main` or `master`, on each pull request, and on a manual start (`workflow_dispatch`). It runs on Python 3.10 and 3.12, and it does these steps:

1. Install the packages in `requirements.txt`.
2. Run `pytest` (all tests run offline).
3. Run `mypy` (strict type check).
4. Run `project2_uganda_tax.ipynb` from top to bottom.

CI does not run `project1_weather.ipynb`, because that notebook calls the live weather APIs and needs a contact email. To see the results, open the **Actions** tab of the repository on GitHub.

## Summary of findings

### Mini-project 1: weather forecast

- The geocoding API leaves out the `results` key when no place matches. The code returns an empty list and then raises `LocationNotFoundError`.
- Some names are ambiguous. "Springfield" gives 10 places in the US. The user picks one with a number in the configuration cell, so "Run All" needs no input.
- `requests` gives shorter and clearer code than `urllib`. It has better error types, and it decodes the response for you.
- All requests go through one client with a timeout, `raise_for_status()`, retries with exponential backoff and a retry cap, and a custom `ApiRequestError`. The notebook tests an invalid city, an invalid latitude, no network (simulated) and a tiny timeout.
- In our run for Kampala (5 October 2026), Open-Meteo and MET Norway agreed on daily temperatures within about 0.5 °C on average. Daily rain differed more (about 4 mm on average), because showers are hard to forecast at one point. The live values change on each run.
- Open-Meteo's free API is for non-commercial use only. MET Norway allows commercial use, but it needs an identifying User-Agent, caching and low traffic. Both need a credit line (CC BY 4.0). A location query is personal data, so a real product must protect it.

### Mini-project 2: Uganda tax engine

- The resident PAYE scale in the brief is the scale of the Income Tax (Amendment) Act 2026, in force from **1 July 2026**. The engine also keeps the older 2012 scale, and selects the scale by date. A date before any scale raises `NoScheduleForDateError`.
- The new scale gives less PAYE to every resident who earns more than UGX 235,000 a month.
- Deduction order: total gross → LST (deductible for PAYE) → PAYE → NSSF (5% employee, 10% employer; it does not reduce the PAYE base) → net pay. Example: gross 2,000,000 + allowances 500,000 in August 2026 gives LST 25,000, PAYE 630,750, NSSF 125,000 and net pay 1,719,250.
- `float` is not safe for tax. For example, `int(4.35 * 100)` gives 434, and three payments of 410,000.10 do not add up to 1,230,000.30. `Money` uses `Decimal` only, with an explicit rule: round half up to a whole shilling.
- We used inheritance for the shared `Tax` interface and the `TaxError` tree. We used composition and data objects for rate schedules, the payroll pipeline, the context and `Money`.
- Extension A (withholding tax and rental income tax) was added with no change to the old classes.

Rate sources (checked 5 October 2026): [URA PAYE rates](https://ura.go.ug/en/domestic-taxes/paye-rates/), [Pulse Uganda](https://www.pulse.ug/story/uganda-new-paye-rates-2026-guide-2026091410372290209), [Sunpro calculator](https://calculator.sunpro.africa/uganda-income-taxation), [LeadAfrik](https://leadafrik.com/tax-rates-uganda), [TaxAtlas](https://taxatlas.io/country/uganda), [Afrotools](https://afrotools.com/uganda/ug-paye), [URA Withholding Tax](https://ura.go.ug/en/witholding-tax/). The full table is at the top of `project2_uganda_tax.ipynb`. All rates are in `src/uganda_tax/rates.py`.

## Data sources and licences

- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0). Geocoding data from GeoNames (CC BY 4.0).
- Forecast data from [MET Norway](https://api.met.no/) (CC BY 4.0 and NLOD 2.0).

## Declaration of AI use

I used **Claude Code** (Anthropic), an AI coding assistant, for these tasks only:

- **Code documentation:** the docstrings and comments in `src/` and `tests/`.
- **README:** the structure and text of this file.
- **Tests:** writing the tests in `tests/` (pytest and Hypothesis) and the saved JSON samples in `tests/data/`.
- **GitHub Actions:** the CI workflow in `.github/workflows/tests.yml`.

I reviewed all the AI output, ran the tests and the notebooks, and can explain each line of the code.
