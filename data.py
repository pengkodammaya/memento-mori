"""
NEKYIA — data layer.

Loads the parquet once at startup and precomputes every aggregation the web app
needs, so the API endpoints stay instant. Also provides soul-sampling for the
interactive "Descent" book.
"""
from __future__ import annotations

import json
import math
import random
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "cod-data.parquet"

# ---------------------------------------------------------------------------
# Vocabulary — bilingual labelling & curatorial groupings.
# Many cause-of-death strings in the source are terse clinical English; we map
# the important ones to a human face and a Bahasa Malaysia gloss, and bucket
# every cause into one of seven archetypal "fates" the app visualises.
# ---------------------------------------------------------------------------

# Bahasa Malaysia glosses for the columns/labels used in the UI.
MS = {
    "age": "Umur",
    "age_at_death": "Umur Saat Meninggal",
    "gender": "Jantina",
    "male": "Lelaki",
    "female": "Perempuan",
    "state": "Negeri",
    "district": "Daerah",
    "ethnicity": "Kumpulan Etnik",
    "cause": "Sebab Kematian",
    "deaths": "Kematian",
    "cause_of_death": "Sebab Kematian",
    "of_malaysian_souls": "jiwa Malaysia",
    "year": "Tahun",
    "years": "tahun",
    "souls": "jiwa",
}

# Curatorial mapping of each cause to one of seven archetypal fates.
# These are the thematic spine of the "Fates That Claim Us" book.
FATE_OF = {
    # The heart & its vessels
    "Ischaemic Heart Diseases": "heart",
    "Cerebrovascular Diseases": "heart",
    "Hypertensive Diseases": "heart",
    "Remainder Of Disease Of The Circulatory System": "heart",
    "Acute Rheumatic Fever And Chronic Rheumatic Heart Disease": "heart",
    "Acute Rheumatic Fever And Chronic Rheumatic Heart Diseases": "heart",
    "Atherosclerosis": "heart",
    # The breath
    "Pneumonia": "breath",
    "Rem. Respiratory": "breath",
    "Chronic Lower Respiratory Diseases": "breath",
    "Respiratory Tuberculosis": "breath",
    "Influenza": "breath",
    # The long shadow — cancer
    "Malignant Neoplasm Of Trachea, Bronchus And Lung": "cancer",
    "Malignant Neoplasm Of Colon, Rectum And Anus": "cancer",
    "Malignant Neoplasm Of Breast": "cancer",
    "Malignant Neoplasm Of Liver And Intrahepatic Bile Ducts": "cancer",
    "Rem. Malignant Neoplasms": "cancer",
    "Malignant Neoplasm Of Pancreas": "cancer",
    "Malignant Neoplasm Of Prostate": "cancer",
    "Malignant Neoplasm Of Stomach": "cancer",
    "Malignant Neoplasm Of Ovary": "cancer",
    "Malignant Neoplasm Of Cervix Uteri": "cancer",
    "Malignant Neoplasm Of Other And Unspecified Parts Of Uterus": "cancer",
    "Malignant Neoplasm Of Meninges, Brain And Other Parts Of Central Nervous System": "cancer",
    "Malignant Neoplasm Of Bladder": "cancer",
    "Malignant Neoplasm Of Oesophagus": "cancer",
    "Multiple Myeloma And Malignant Plasma Cell Neoplasms": "cancer",
    "Malignant Neoplasm Of Larynx": "cancer",
    "Malignant Melanoma Of Skin": "cancer",
    "Leukaemia": "cancer",
    "Non-Hodgkins Lymphoma": "cancer",
    "Malignant Neoplasm Of Lip, Oral Cavity And Pharynx": "cancer",
    # The body's rebellion — metabolic & organ
    "Diabetes Mellitus": "metabolic",
    "Diseases Of The Liver": "metabolic",
    "Gastric And Duodenal Ulcer": "metabolic",
    "Glomerular And Renal Tubulo-Interstitial Diseases": "metabolic",
    "Anaemias": "metabolic",
    "Malnutrition": "metabolic",
    # Pestilence — infection & pandemic
    "Covid-19 Infection (Due To)": "pestilence",
    "Rem. Infectious & Parasitic": "pestilence",
    "Human Immunodeficiency Virus (Hiv) Disease": "pestilence",
    "Viral Hepatitis": "pestilence",
    "Meningitis": "pestilence",
    "Diarrhoea And Gastroenteritis Of Presumed Infectious Origin": "pestilence",
    "Malaria": "pestilence",
    "Rabies": "pestilence",
    "Influenza": "pestilence",  # also breath; pestilence wins for grouping
    "Whooping Cough": "pestilence",
    "Infections With A Predominantly Sexual Mode Of Transmission": "pestilence",
    "Meningococcal Infection": "pestilence",
    "Tetanus": "pestilence",
    "Diphtheria": "pestilence",
    "Measles": "pestilence",
    "Cholera": "pestilence",
    "Acute Poliomyelitis": "pestilence",
    "Respiratory Tuberculosis": "pestilence",
    # Violence — accident & intent
    "Transport Accidents": "violence",
    "Intentional Self-Harm": "violence",
    "Accidental Drowning And Submersion": "violence",
    "Falls": "violence",
    "Assault": "violence",
    "Accidental Poisoning By And Exposure To Noxious Substances": "violence",
    "Exposure To Smoke, Fire And Flame": "violence",
    # The dawn & the unknown — beginnings and the mind
    "Certain Conditions Originating In The Perinatal Period": "dawn",
    "Congenital Malformations, Deformations And Chromosomal Abnormalities": "dawn",
    "Indirect Obstetric Deaths": "dawn",
    "Pregnancy With Abortive Outcome": "dawn",
    "Alzheimers Disease": "dawn",
    "Mental And Behavioural Disoder Due To Psychoactive Sustance Use": "dawn",
}

FATE_META = {
    "heart": {
        "label": "The Heart & Its Vessels",
        "ms": "Jantung & Salurannya",
        "color": "#c8323a",
        "glyph": "❦",
        "odyssey": "the slow tide that fells kings and fishermen alike",
    },
    "breath": {
        "label": "The Failing Breath",
        "ms": "Nafas yang Melemah",
        "color": "#7fb8c4",
        "glyph": "≈",
        "odyssey": "the lung's long surrender to the air",
    },
    "cancer": {
        "label": "The Long Shadow",
        "ms": "Bayang Panjang",
        "color": "#9b6db5",
        "glyph": "✶",
        "odyssey": "the cell that forgets how to die, and so becomes death",
    },
    "metabolic": {
        "label": "The Body's Rebellion",
        "ms": "Pemberontakan Tubuh",
        "color": "#d4a13a",
        "glyph": "◈",
        "odyssey": "sweet blood and broken organs turning inward",
    },
    "pestilence": {
        "label": "Pestilence",
        "ms": "Wabak",
        "color": "#6fae5a",
        "glyph": "☣",
        "odyssey": "the invisible army that crossed every sea",
    },
    "violence": {
        "label": "Violence & Chance",
        "ms": "Keganasan & Nasib",
        "color": "#d96b3c",
        "glyph": "⚔",
        "odyssey": "the sudden storm, the careless edge, the hand turned against itself",
    },
    "dawn": {
        "label": "The Dawn & the Unknown",
        "ms": "Fajar & yang Tersembunyi",
        "color": "#8aa0b8",
        "glyph": "☾",
        "odyssey": "those who never saw noon, and those whose minds drifted out with the tide",
    },
}

# Friendlier display name for causes (strip ICD-style noise, fix quotes/case).
def _pretty_cause(name: str) -> str:
    n = name.strip().strip('"')
    # Title-case but keep common medical lowercased words readable.
    return n


# Province-ish grouping for the Archipelago book — Malay states by region.
REGION_OF = {
    "Johor": "Selatan",
    "Melaka": "Selatan",
    "Negeri Sembilan": "Selatan",
    "Selangor": "Tengah",
    "W.P. Kuala Lumpur": "Tengah",
    "W.P. Putrajaya": "Tengah",
    "Pahang": "Tengah",
    "Perak": "Utara",
    "Pulau Pinang": "Utara",
    "Kedah": "Utara",
    "Perlis": "Utara",
    "Kelantan": "Timur",
    "Terengganu": "Timur",
    "Sabah": "Borneo",
    "Sarawak": "Borneo",
    "W.P. Labuan": "Borneo",
}

REGION_LABEL = {
    "Utara": ("The Northern Shores", "Pantai Utara"),
    "Tengah": ("The Heartlands", "Tanduk Tengah"),
    "Selatan": ("The Southern Gate", "Pintu Selatan"),
    "Timur": ("The East Wind", "Angin Timur"),
    "Borneo": ("The Isles of Borneo", "Kepulauan Borneo"),
}


# ---------------------------------------------------------------------------
# Loading & precomputation
# ---------------------------------------------------------------------------

class Catalogue:
    """Holds the loaded dataframe and every precomputed view."""

    def __init__(self, path: Path = DATA_PATH) -> None:
        self.df = pd.read_parquet(path)
        self.df["cause_pretty"] = self.df["sebab_kematian"].map(_pretty_cause)
        self.df["fate"] = self.df["sebab_kematian"].map(
            lambda s: FATE_OF.get(s.strip().strip('"'), "dawn")
        )
        # age bins used across several books
        self.df["age_bin"] = pd.cut(
            self.df["umur"],
            bins=[-1, 0, 4, 14, 24, 44, 64, 200],
            labels=["<1", "1–4", "5–14", "15–24", "25–44", "45–64", "65+"],
        )

        self.total = int(len(self.df))
        self._compute()

    # -- precomputed views -------------------------------------------------
    def _compute(self) -> None:
        d = self.df

        # Overall
        self.overview = {
            "total": self.total,
            "male": int((d["jantina"] == "Lelaki").sum()),
            "female": int((d["jantina"] == "Perempuan").sum()),
            "median_age": float(d["umur"].median()),
            "mean_age": round(float(d["umur"].mean()), 1),
            "oldest": int(d["umur"].max()),
            "youngest_recorded": 0,
            "n_causes": int(d["sebab_kematian"].nunique()),
            "n_states": int(d["negeri"].nunique()),
            "n_districts": int(d["daerah"].nunique()),
        }

        # Fates (the seven archetypal groupings)
        self.fates = self._fates()

        # Top causes (full ranked list)
        vc = d["cause_pretty"].value_counts()
        self.causes = [
            {"cause": k, "count": int(v), "pct": round(v / self.total * 100, 2)}
            for k, v in vc.items()
        ]

        # Age voyage — single-year and binned
        self.age_single = [
            {"age": int(a), "count": int(c)}
            for a, c in d["umur"].value_counts().sort_index().items()
        ]
        binned = d["age_bin"].value_counts().sort_index()
        self.age_binned = [
            {"bin": str(b), "count": int(c)} for b, c in binned.items()
        ]

        # Age by gender (for the voyage chart overlay)
        ag = (
            d.groupby(["umur", "jantina"], observed=True)
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )
        self.age_by_gender = [
            {
                "age": int(a),
                "male": int(row.get("Lelaki", 0)),
                "female": int(row.get("Perempuan", 0)),
            }
            for a, row in ag.iterrows()
        ]

        # Archipelago — states with region, plus a sample of districts
        st = d["negeri"].value_counts()
        self.states = []
        for state, count in st.items():
            sub = d[d["negeri"] == state]
            top_districts = (
                sub["daerah"]
                .value_counts()
                .head(6)
                .items()
            )
            self.states.append(
                {
                    "state": state,
                    "region": REGION_OF.get(state, "—"),
                    "count": int(count),
                    "pct": round(count / self.total * 100, 2),
                    "top_districts": [
                        {"district": dk, "count": int(dv)} for dk, dv in top_districts
                    ],
                }
            )
        # region rollup
        self.regions = {}
        for state in self.states:
            r = state["region"]
            self.regions.setdefault(r, 0)
            self.regions[r] += state["count"]

        # Ethnicities
        et = d["etnik"].value_counts()
        self.ethnicities = [
            {"ethnicity": k, "count": int(v), "pct": round(v / self.total * 100, 2)}
            for k, v in et.items()
        ]

        # Specific poignant cross-tabs for the narrative
        self.infant = int((d["umur"] < 1).sum())
        self.children_5_14 = int(((d["umur"] >= 5) & (d["umur"] <= 14)).sum())
        self.young_adults = int(((d["umur"] >= 15) & (d["umur"] <= 24)).sum())
        self.elders = int((d["umur"] >= 65).sum())
        self.centenarians = int((d["umur"] >= 95).sum())

        # Transport accidents peak age
        ta = d[d["sebab_kematian"].str.contains("Transport Accidents", na=False)]
        if len(ta):
            self.transport_peak_age = int(ta["umur"].mode().iloc[0])
            self.transport_young = int(
                ((ta["umur"] >= 15) & (ta["umur"] <= 34)).sum()
            )
        else:
            self.transport_peak_age, self.transport_young = 0, 0

        # Self-harm
        sh = d[d["sebab_kematian"].str.contains("Intentional Self-Harm", na=False)]
        self.self_harm_total = int(len(sh))
        self.self_harm_male = int((sh["jantina"] == "Lelaki").sum())
        self.self_harm_peak_age = (
            int(sh["umur"].mode().iloc[0]) if len(sh) else 0
        )

    def _fates(self) -> list[dict]:
        d = self.df
        out = []
        for key, meta in FATE_META.items():
            sub = d[d["fate"] == key]
            count = int(len(sub))
            if count == 0:
                continue
            top = (
                sub["cause_pretty"]
                .value_counts()
                .head(3)
                .items()
            )
            out.append(
                {
                    "key": key,
                    "label": meta["label"],
                    "ms": meta["ms"],
                    "color": meta["color"],
                    "glyph": meta["glyph"],
                    "odyssey": meta["odyssey"],
                    "count": count,
                    "pct": round(count / self.total * 100, 2),
                    "median_age": (
                        round(float(sub["umur"].median()), 1) if count else 0
                    ),
                    "top_causes": [
                        {"cause": k, "count": int(v)} for k, v in top
                    ],
                }
            )
        out.sort(key=lambda x: x["count"], reverse=True)
        return out

    # -- interactive soul sampling ----------------------------------------
    @lru_cache(maxsize=1)
    def _indexed(self) -> tuple[pd.DataFrame, dict]:
        """Return df plus an index lookup for fast filtering."""
        return self.df, {}

    def sample_souls(
        self,
        cause: str | None = None,
        state: str | None = None,
        ethnicity: str | None = None,
        gender: str | None = None,
        age_min: int | None = None,
        age_max: int | None = None,
        n: int = 1,
        seed: int | None = None,
    ) -> list[dict]:
        """Return up to `n` anonymised individual records as 'souls'.

        Each soul is one real row from the catalogue, but presented as a
        mythic persona rather than raw data — to keep the experience
        respectful, no free-text identifiers exist in the source anyway.
        """
        d = self.df
        mask = pd.Series(True, index=d.index)
        if cause:
            mask &= d["cause_pretty"] == cause
        if state:
            mask &= d["negeri"] == state
        if ethnicity:
            mask &= d["etnik"] == ethnicity
        if gender:
            mapped = {"male": "Lelaki", "female": "Perempuan"}.get(gender, gender)
            mask &= d["jantina"] == mapped
        if age_min is not None:
            mask &= d["umur"] >= age_min
        if age_max is not None:
            mask &= d["umur"] <= age_max

        sub = d[mask]
        if len(sub) == 0:
            return []

        rng = random.Random(seed)
        n = min(n, len(sub))
        # sample positional indices via the rng for reproducibility
        positions = sorted(rng.sample(range(len(sub)), n))
        sampled = sub.iloc[positions]

        souls = []
        for _, row in sampled.iterrows():
            fate_key = FATE_OF.get(
                str(row["sebab_kematian"]).strip().strip('"'), "dawn"
            )
            souls.append(
                {
                    "age": int(row["umur"]),
                    "gender": "male" if row["jantina"] == "Lelaki" else "female",
                    "gender_ms": row["jantina"],
                    "state": row["negeri"],
                    "district": row["daerah"],
                    "ethnicity": row["etnik"],
                    "cause": row["cause_pretty"],
                    "fate": fate_key,
                    "fate_label": FATE_META[fate_key]["label"],
                    "fate_glyph": FATE_META[fate_key]["glyph"],
                    "fate_color": FATE_META[fate_key]["color"],
                }
            )
        return souls

    # -- introspection helpers used by the API/UI -------------------------
    def cause_list(self) -> list[str]:
        return [c["cause"] for c in self.causes]

    def state_list(self) -> list[str]:
        return [s["state"] for s in self.states]

    def ethnicity_list(self) -> list[str]:
        return [e["ethnicity"] for e in self.ethnicities]

    def region_label(self, key: str) -> tuple[str, str]:
        return REGION_LABEL.get(key, (key, key))


# Module-level singleton, loaded lazily on first access.
_catalogue: Catalogue | None = None


def get_catalogue() -> Catalogue:
    global _catalogue
    if _catalogue is None:
        _catalogue = Catalogue()
    return _catalogue


if __name__ == "__main__":
    # Smoke test: print the headline numbers.
    c = get_catalogue()
    print(f"Total souls: {c.total:,}")
    print(f"Causes: {len(c.causes)}  States: {len(c.states)}")
    print("Fates:")
    for f in c.fates:
        print(f"  {f['glyph']} {f['label']:<28} {f['count']:>7,}  ({f['pct']}%)")
    print("\nSample soul:", json.dumps(c.sample_souls(n=1, seed=42)[0], indent=2))
