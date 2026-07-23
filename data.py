"""
NEKYIA — data layer (runtime).

Reads precomputed cache files produced by `precompute.py` — no pandas or
pyarrow needed at runtime. The Catalogue class keeps the same public API as
the original pandas-backed implementation, so the Flask app is unchanged.

Cache files (committed in data_cache/):
  - aggregations.json   every precomputed view the API serves (~20 KB)
  - souls.npz           748,934 rows as compact int arrays (~1 MB)
"""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

import numpy as np

CACHE_DIR = Path(__file__).parent / "data_cache"
DATA_PATH = Path(__file__).parent / "cod-data.parquet"  # source of truth

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
# Loading — reads the precomputed cache (no pandas / pyarrow at runtime).
# ---------------------------------------------------------------------------

class Catalogue:
    """Holds the precomputed views and the compact soul-pool for sampling."""

    def __init__(self) -> None:
        agg = json.loads((CACHE_DIR / "aggregations.json").read_text(encoding="utf-8"))

        # Precomputed views — served straight back by the API.
        self.total: int = agg["total"]
        self.overview = agg["overview"]
        self.fates = agg["fates"]
        self.causes = agg["causes"]
        self.age_single = agg["age_single"]
        self.age_binned = agg["age_binned"]
        self.age_by_gender = agg["age_by_gender"]
        self.states = agg["states"]
        self.regions = agg["regions"]
        self.ethnicities = agg["ethnicities"]
        self.infant: int = agg["infant"]
        self.children_5_14: int = agg["children_5_14"]
        self.young_adults: int = agg["young_adults"]
        self.elders: int = agg["elders"]
        self.centenarians: int = agg["centenarians"]
        self.transport_peak_age: int = agg["transport_peak_age"]
        self.transport_young: int = agg["transport_young"]
        self.self_harm_total: int = agg["self_harm_total"]
        self.self_harm_male: int = agg["self_harm_male"]
        self.self_harm_peak_age: int = agg["self_harm_peak_age"]

        # Soul-pool — integer arrays for the interactive Descent endpoint.
        npz = np.load(CACHE_DIR / "souls.npz", allow_pickle=False)
        self._age = npz["age"]
        self._gender = npz["gender"]
        self._state = npz["state"]
        self._district = npz["district"]
        self._ethnicity = npz["ethnicity"]
        self._cause = npz["cause"]
        self._fate = npz["fate"]
        self._raw_cause = npz["raw_cause"]
        vocab = json.loads(str(npz["vocab"]))
        self._vocab = vocab

    # -- interactive soul sampling ----------------------------------------
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

        Reproducibility note: this mirrors the original pandas implementation
        exactly. We build a boolean mask over all rows, materialise the
        filtered positions, then `random.Random(seed).sample(those positions,
        n)` — same RNG, same positional sampling, same row order.
        """
        mask = np.ones(len(self._age), dtype=bool)
        if cause:
            mask &= self._cause == self._cause_lookup(cause, "cause")
        if state:
            mask &= self._state == self._state_lookup(state)
        if ethnicity:
            mask &= self._ethnicity == self._eth_lookup(ethnicity)
        if gender:
            mapped = {"male": "Lelaki", "female": "Perempuan"}.get(gender, gender)
            mask &= self._gender == self._gender_lookup(mapped)
        if age_min is not None:
            mask &= self._age >= age_min
        if age_max is not None:
            mask &= self._age <= age_max

        positions = np.nonzero(mask)[0]
        if len(positions) == 0:
            return []

        rng = random.Random(seed)
        n = min(n, len(positions))
        # Sample positional indices within the filtered subset, sorted as the
        # original did (so the returned order is ascending by row position).
        chosen = sorted(rng.sample(range(len(positions)), n))
        idx = positions[chosen]

        return [self._soul_at(i) for i in idx]

    # -- introspection helpers used by the API/UI -------------------------
    def cause_list(self) -> list[str]:
        return [c["cause"] for c in self.causes]

    def state_list(self) -> list[str]:
        return [s["state"] for s in self.states]

    def ethnicity_list(self) -> list[str]:
        return [e["ethnicity"] for e in self.ethnicities]

    def region_label(self, key: str) -> tuple[str, str]:
        return REGION_LABEL.get(key, (key, key))

    # -- private: build a soul dict from a flat row index -----------------
    def _soul_at(self, i: int) -> dict:
        v = self._vocab
        gender_ms = v["gender"][int(self._gender[i])]
        raw_cause = v["raw_cause"][int(self._raw_cause[i])]
        fate_key = FATE_OF.get(raw_cause.strip().strip('"'), "dawn")
        return {
            "age": int(self._age[i]),
            "gender": "male" if gender_ms == "Lelaki" else "female",
            "gender_ms": gender_ms,
            "state": v["state"][int(self._state[i])],
            "district": v["district"][int(self._district[i])],
            "ethnicity": v["ethnicity"][int(self._ethnicity[i])],
            "cause": v["cause"][int(self._cause[i])],
            "fate": fate_key,
            "fate_label": FATE_META[fate_key]["label"],
            "fate_glyph": FATE_META[fate_key]["glyph"],
            "fate_color": FATE_META[fate_key]["color"],
        }

    # -- private: vocab lookup caches -------------------------------------
    @lru_cache(maxsize=None)
    def _cause_lookup(self, value: str, column: str) -> int:
        return self._vocab[column].index(value)

    @lru_cache(maxsize=None)
    def _state_lookup(self, value: str) -> int:
        return self._vocab["state"].index(value)

    @lru_cache(maxsize=None)
    def _eth_lookup(self, value: str) -> int:
        return self._vocab["ethnicity"].index(value)

    @lru_cache(maxsize=None)
    def _gender_lookup(self, value: str) -> int:
        return self._vocab["gender"].index(value)


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
