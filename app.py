"""
NEKYIA — The Catalogue of Souls.

A Flask app that presents Malaysian cause-of-death data as a voyage through
the underworld, inspired by Book XI of Homer's Odyssey.

Run:
    python app.py
then open http://127.0.0.1:5000
"""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from data import get_catalogue

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """The single-page voyage. All books render client-side from the API."""
    cat = get_catalogue()
    return render_template("index.html", overview=cat.overview)


# ---------------------------------------------------------------------------
# JSON API — each endpoint feeds one "book" of the voyage.
# ---------------------------------------------------------------------------

@app.route("/api/overview")
def api_overview():
    cat = get_catalogue()
    return jsonify(cat.overview)


@app.route("/api/fates")
def api_fates():
    """Book XI — the seven archetypal fates that claim Malaysian souls."""
    cat = get_catalogue()
    return jsonify({"total": cat.total, "fates": cat.fates})


@app.route("/api/causes")
def api_causes():
    """Full ranked list of individual causes (drill-down beneath the fates)."""
    cat = get_catalogue()
    return jsonify({"causes": cat.causes, "total": cat.total})


@app.route("/api/age")
def api_age():
    """Book IX — the voyage of years. Returns binned, single-year, and by-gender."""
    cat = get_catalogue()
    return jsonify(
        {
            "binned": cat.age_binned,
            "single": cat.age_single,
            "by_gender": cat.age_by_gender,
            "median": cat.overview["median_age"],
            "mean": cat.overview["mean_age"],
        }
    )


@app.route("/api/archipelago")
def api_archipelago():
    """Book III — the states of Malaysia as islands in the wine-dark sea."""
    cat = get_catalogue()
    regions = []
    for key, count in sorted(cat.regions.items(), key=lambda x: -x[1]):
        en, ms = cat.region_label(key)
        regions.append({"key": key, "label": en, "ms": ms, "count": count})
    return jsonify(
        {
            "states": cat.states,
            "regions": regions,
            "ethnicities": cat.ethnicities,
        }
    )


@app.route("/api/souls")
def api_souls():
    """Book XI (Descent) — summon individual souls by filter.

    This is the heart of the interactive experience: the visitor pours an
    offering (sets filters) and the catalogue returns anonymised individual
    records, presented as souls encountered at the edge of the underworld.
    """
    cat = get_catalogue()

    def _arg(name):
        v = request.args.get(name)
        return v if v not in (None, "", "null") else None

    cause = _arg("cause")
    state = _arg("state")
    ethnicity = _arg("ethnicity")
    gender = _arg("gender")
    age_min = _arg("age_min")
    age_max = _arg("age_max")
    seed = _arg("seed")

    age_min = int(age_min) if age_min is not None else None
    age_max = int(age_max) if age_max is not None else None

    try:
        n = int(request.args.get("n", 1))
    except ValueError:
        n = 1
    n = max(1, min(n, 12))

    seed_int = None
    if seed is not None:
        try:
            seed_int = int(seed)
        except ValueError:
            seed_int = sum(ord(c) for c in str(seed))

    souls = cat.sample_souls(
        cause=cause,
        state=state,
        ethnicity=ethnicity,
        gender=gender,
        age_min=age_min,
        age_max=age_max,
        n=n,
        seed=seed_int,
    )
    return jsonify(
        {
            "count": len(souls),
            "souls": souls,
            "filters": {
                "cause": cause,
                "state": state,
                "ethnicity": ethnicity,
                "gender": gender,
                "age_min": age_min,
                "age_max": age_max,
            },
        }
    )


@app.route("/api/facets")
def api_facets():
    """Filter option lists for the Descent form."""
    cat = get_catalogue()
    return jsonify(
        {
            "causes": cat.cause_list(),
            "states": cat.state_list(),
            "ethnicities": cat.ethnicity_list(),
            "genders": ["male", "female"],
        }
    )


if __name__ == "__main__":
    # Warm the catalogue before serving so the first request is instant.
    print("Loading the catalogue of souls…")
    get_catalogue()
    print("The catalogue is open. Set sail → http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
