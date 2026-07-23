"""
NEKYIA — precompute step.

Run this locally (in an env with pandas + pyarrow + numpy) to regenerate the
runtime data cache. The deployed app reads only the cache files, so the
heavy libraries never need to be installed in production.

Run:
    python precompute.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import DATA_PATH, FATE_OF, Catalogue

CACHE_DIR = Path(__file__).parent / "data_cache"


def main() -> None:
    print("Loading catalogue (this uses pandas + pyarrow)…")
    cat = Catalogue()

    CACHE_DIR.mkdir(exist_ok=True)

    # -------------------------------------------------------------------
    # 1. Aggregations JSON — every precomputed view the API serves.
    # -------------------------------------------------------------------
    aggregations = {
        "total": cat.total,
        "overview": cat.overview,
        "fates": cat.fates,
        "causes": cat.causes,
        "age_single": cat.age_single,
        "age_binned": cat.age_binned,
        "age_by_gender": cat.age_by_gender,
        "states": cat.states,
        "regions": cat.regions,
        "ethnicities": cat.ethnicities,
        "infant": cat.infant,
        "children_5_14": cat.children_5_14,
        "young_adults": cat.young_adults,
        "elders": cat.elders,
        "centenarians": cat.centenarians,
        "transport_peak_age": cat.transport_peak_age,
        "transport_young": cat.transport_young,
        "self_harm_total": cat.self_harm_total,
        "self_harm_male": cat.self_harm_male,
        "self_harm_peak_age": cat.self_harm_peak_age,
    }
    agg_path = CACHE_DIR / "aggregations.json"
    agg_path.write_text(json.dumps(aggregations, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {agg_path} ({agg_path.stat().st_size / 1024:.1f} KB)")

    # -------------------------------------------------------------------
    # 2. Souls NPZ — the 748,934 rows as compact integer arrays, for the
    #    interactive /api/souls endpoint. Strings are factorised to ints and
    #    stored alongside their lookup tables.
    # -------------------------------------------------------------------
    df = cat.df
    n = len(df)

    def factorise(series: pd.Series) -> tuple[np.ndarray, list[str]]:
        codes, uniques = pd.factorize(series, sort=True)
        return codes.astype(np.int32), [str(u) for u in uniques]

    age = df["umur"].to_numpy(dtype=np.int16)
    gender_codes, gender_vals = factorise(df["jantina"])
    state_codes, state_vals = factorise(df["negeri"])
    district_codes, district_vals = factorise(df["daerah"])
    ethnicity_codes, ethnicity_vals = factorise(df["etnik"])
    # cause_pretty and fate are already derived by Catalogue.__init__
    cause_codes, cause_vals = factorise(df["cause_pretty"])
    fate_codes, fate_vals = factorise(df["fate"])
    # Raw sebab_kematian kept too — needed to resolve the fate label at sample
    # time (cause_pretty is the display name; the raw string maps to FATE_OF).
    raw_cause_codes, raw_cause_vals = factorise(df["sebab_kematian"])

    npz_path = CACHE_DIR / "souls.npz"
    np.savez_compressed(
        npz_path,
        age=age,
        gender=gender_codes,
        state=state_codes,
        district=district_codes,
        ethnicity=ethnicity_codes,
        cause=cause_codes,
        fate=fate_codes,
        raw_cause=raw_cause_codes,
        # String lookup tables as a single JSON blob (numpy doesn't do strings).
        vocab=json.dumps(
            {
                "gender": gender_vals,
                "state": state_vals,
                "district": district_vals,
                "ethnicity": ethnicity_vals,
                "cause": cause_vals,
                "fate": fate_vals,
                "raw_cause": raw_cause_vals,
            },
            ensure_ascii=False,
        ),
    )
    print(f"  wrote {npz_path} ({npz_path.stat().st_size / 1024 / 1024:.2f} MB)")

    # -------------------------------------------------------------------
    # 3. Verification summary — sanity-check totals and row counts.
    # -------------------------------------------------------------------
    print("\n=== verification ===")
    print(f"  total souls: {n:,}  (parquet rows match)")
    assert n == cat.total, "row count mismatch!"
    print(f"  unique causes: {len(cause_vals)}")
    print(f"  unique states: {len(state_vals)}")
    print(f"  unique ethnicities: {len(ethnicity_vals)}")
    print(f"  unique districts: {len(district_vals)}")
    print(f"  fate codes present: {sorted(set(fate_codes.tolist()))}")
    print(f"  gender codes present: {sorted(set(gender_codes.tolist()))}")
    print("\nDone. Commit data_cache/ — the runtime reads only these files.")


if __name__ == "__main__":
    main()
