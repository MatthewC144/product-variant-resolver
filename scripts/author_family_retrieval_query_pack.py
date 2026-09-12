#!/usr/bin/env python3
"""Materialize the independently written T48 family-retrieval query pack."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "evaluation/family-retrieval-v1/query-pack.json"
AUTHORED_AT = "2026-09-12T16:30:00Z"

# Each tuple is: marketplace query, marketplace tags, lexical query, lexical tags.
# These strings were composed before any T48 retrieval result existed.
POSITIVE_QUERIES: dict[str, tuple[str, list[str], str, list[str]]] = {
    "fandom-family-0573861db69878eb": (
        "Max Steel blue loose fantasy car seller lot",
        ["condition_noise", "seller_wrapper"],
        "max steal racer on short card",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-08cb7fadb9fed12d": (
        "2025 Hot Wheels 1988 Jeep Wagoneer red sealed card",
        ["condition_noise", "marketplace_wrapper", "year_noise"],
        "HW 88 jeep wagoner loose truck",
        ["abbreviation", "misspelling", "seller_wrapper"],
    ),
    "fandom-family-1555c05ceeb491cb": (
        "Hot Wheels '94 Audi Avant RS2 silver mint on card",
        ["condition_noise", "marketplace_wrapper"],
        "94 audi avnt rs 2 wagon diecast",
        ["misspelling", "spacing"],
    ),
    "fandom-family-174efb9bce3a441e": (
        "Lamborghini Huracán Sterrato orange unopened collector car",
        ["condition_noise", "seller_wrapper"],
        "lambo huracan sterato off road model",
        ["abbreviation", "misspelling"],
    ),
    "fandom-family-18e55e067083dbd1": (
        "2025 '87 Audi quattro blue Hot Wheels mainline sealed",
        ["condition_noise", "series_noise", "year_noise"],
        "87 audi quatro rally car loose",
        ["misspelling", "seller_wrapper"],
    ),
    "fandom-family-1b2a4227b4e5decd": (
        "Mercedes-Benz 500 E black premium style diecast lot",
        ["marketplace_wrapper", "seller_wrapper"],
        "mercedes benz five hundred e sedan",
        ["punctuation", "spacing"],
    ),
    "fandom-family-2357e7eb6b4e62b8": (
        "Monster High Ghoul Mobile pink carded fantasy vehicle",
        ["condition_noise", "marketplace_wrapper"],
        "monsterhi ghoulmobile toy car",
        ["spacing", "seller_wrapper"],
    ),
    "fandom-family-356e4ef63275a661": (
        "Fish'd & Chip'd green Hot Wheels sealed seller listing",
        ["condition_noise", "seller_wrapper"],
        "fish n chipped novelty car loose",
        ["punctuation", "spacing"],
    ),
    "fandom-family-39b248ce2f3723cd": (
        "Twin Mill Gen-E silver carded electric concept car",
        ["condition_noise", "marketplace_wrapper"],
        "twinmill gen e ev model",
        ["punctuation", "spacing"],
    ),
    "fandom-family-3c9f928f085efaae": (
        "Kick Kart yellow Hot Wheels new in package",
        ["condition_noise", "marketplace_wrapper"],
        "kik kart fantasy racer",
        ["misspelling", "seller_wrapper"],
    ),
    "fandom-family-440103f8ef3c6b70": (
        "Haulerback purple short card mint collector listing",
        ["condition_noise", "seller_wrapper"],
        "haulerbak truck model",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-45af5b93f3f6650f": (
        "Custom Cadillac Fleetwood gold loose Hot Wheels auction",
        ["condition_noise", "seller_wrapper"],
        "custom caddy fleetwd lowrider",
        ["abbreviation", "misspelling"],
    ),
    "fandom-family-4bf5341a133d433b": (
        "Hirohata Merc teal carded custom car collector sale",
        ["condition_noise", "seller_wrapper"],
        "hirohata mercury custom loose",
        ["abbreviation", "marketplace_wrapper"],
    ),
    "fandom-family-4d00e96d12341b4d": (
        "Nerve Hammer orange Hot Wheels blister pack listing",
        ["condition_noise", "marketplace_wrapper"],
        "nerv hammer fantasy car",
        ["misspelling", "seller_wrapper"],
    ),
    "fandom-family-4d2de6db3d5bba63": (
        "Crescendo red music themed car sealed on card",
        ["condition_noise", "seller_wrapper"],
        "crescndo fantasy model",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-526b697937fde7cc": (
        "Hot Wheels '80 El Camino black 2025 carded pickup",
        ["condition_noise", "marketplace_wrapper", "year_noise"],
        "eighties elcamino ute loose",
        ["spacing", "seller_wrapper"],
    ),
    "fandom-family-57cf5c31afbadc57": (
        "The Vanster green Hot Wheels unopened van listing",
        ["condition_noise", "seller_wrapper"],
        "vanstr custom van toy",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-59e5682e50af879e": (
        "Proton Saga white Hot Wheels 2025 mint card",
        ["condition_noise", "marketplace_wrapper", "year_noise"],
        "protn saga malaysia sedan",
        ["misspelling", "seller_wrapper"],
    ),
    "fandom-family-7e221ec8ecd02815": (
        "X-34 Landspeeder tan Star Wars Hot Wheels carded",
        ["condition_noise", "series_noise"],
        "x34 land speeder sci fi vehicle",
        ["punctuation", "spacing"],
    ),
    "fandom-family-85226ac5ac0d3f77": (
        "Fiat 500e yellow electric city car sealed blister",
        ["condition_noise", "seller_wrapper"],
        "fiat five hundred e mini ev",
        ["spacing", "marketplace_wrapper"],
    ),
    "fandom-family-85e407525ac7bf41": (
        "Small Bloc blue Hot Wheels short card seller lot",
        ["condition_noise", "seller_wrapper"],
        "small block fantasy coupe",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-89930c384be2e8bf": (
        "Kowloon'd Hypervan red carded Hong Kong van",
        ["condition_noise", "marketplace_wrapper"],
        "kowloon hyper van street model",
        ["punctuation", "spacing"],
    ),
    "fandom-family-8a07157f2af2ddd5": (
        "Bogzilla green monster fantasy car unopened blister",
        ["condition_noise", "seller_wrapper"],
        "bogzila creature vehicle",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-8cce01fa7d44112a": (
        "Deora III purple Hot Wheels new on short card",
        ["condition_noise", "marketplace_wrapper"],
        "deora 3 surf truck",
        ["spacing", "seller_wrapper"],
    ),
    "fandom-family-9069156ec909a92e": (
        "Donut Drifter pink bakery car sealed collector item",
        ["condition_noise", "seller_wrapper"],
        "donut drift pastry racer",
        ["abbreviation", "marketplace_wrapper"],
    ),
    "fandom-family-99200212d1475ef2": (
        "2025 Hot Wheels 2020 Ram 1500 Rebel pickup sealed",
        ["condition_noise", "marketplace_wrapper", "year_noise"],
        "ram fifteen hundred rebl truck",
        ["misspelling", "spacing"],
    ),
    "fandom-family-a1b198f7d235f778": (
        "Ford Performance SuperVan 4 white carded race van",
        ["condition_noise", "seller_wrapper"],
        "ford perf super van four electric racer",
        ["abbreviation", "spacing"],
    ),
    "fandom-family-a2097eead3bd8db9": (
        "Hot Wheels '66 Buick Riviera teal mint blister",
        ["condition_noise", "marketplace_wrapper"],
        "sixty six buick riv custom",
        ["abbreviation", "spacing"],
    ),
    "fandom-family-a8e0dec4abdc4131": (
        "DMC DeLorean silver time machine car sealed card",
        ["condition_noise", "series_noise"],
        "d m c deloran movie car",
        ["misspelling", "spacing"],
    ),
    "fandom-family-aab5350cb90d72ed": (
        "Hot Wheels '21 Ford Bronco blue mainline unopened",
        ["condition_noise", "series_noise"],
        "2021 frd bronco off road toy",
        ["misspelling", "spacing"],
    ),
    "fandom-family-aaafff57ac4d4daa": (
        "Morgan Super 3 red three wheeler sealed listing",
        ["condition_noise", "seller_wrapper"],
        "morgan super three roadster",
        ["spacing", "marketplace_wrapper"],
    ),
    "fandom-family-aec11693bfe04245": (
        "Mazda REPU orange pickup Hot Wheels carded sale",
        ["condition_noise", "seller_wrapper"],
        "mazda r e p u rotary truck",
        ["abbreviation", "spacing"],
    ),
    "fandom-family-b31d285560d8a242": (
        "Ford Mustang GTD grey 2025 sealed collector car",
        ["condition_noise", "seller_wrapper", "year_noise"],
        "ford mustng g t d supercar",
        ["misspelling", "spacing"],
    ),
    "fandom-family-b3cd4f5a5f7e196a": (
        "Hot Wheels '69 Corvette Racer yellow blister pack",
        ["condition_noise", "marketplace_wrapper"],
        "69 corvett race car loose",
        ["misspelling", "seller_wrapper"],
    ),
    "fandom-family-c655fb5244c584ae": (
        "Kei Swap red Japanese mini truck sealed listing",
        ["condition_noise", "seller_wrapper"],
        "kei swp custom microvan",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-d114c33db6fa215b": (
        "Hot Wheels '90 Honda Civic EF white carded import",
        ["condition_noise", "marketplace_wrapper"],
        "ninety honda civic ef hatch",
        ["spacing", "seller_wrapper"],
    ),
    "fandom-family-d5c83bb87be8cab0": (
        "Super Twin Mill chrome Hot Wheels new in blister",
        ["condition_noise", "marketplace_wrapper"],
        "supertwin mill fantasy racer",
        ["spacing", "seller_wrapper"],
    ),
    "fandom-family-d816204cf649a0c0": (
        "Draftnator black fantasy racer mint on card",
        ["condition_noise", "seller_wrapper"],
        "draftn8r race car",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-d90841788b1d98a2": (
        "Alpha Pursuit police car blue sealed Hot Wheels",
        ["condition_noise", "seller_wrapper"],
        "alfa pursuit patrol vehicle",
        ["misspelling", "marketplace_wrapper"],
    ),
    "fandom-family-db3fe3a0103099ec": (
        "Hot Wheels '22 Ford Maverick Custom red carded truck",
        ["condition_noise", "marketplace_wrapper"],
        "ford mavrick custom 2022 pickup",
        ["misspelling", "spacing"],
    ),
    "fandom-family-e7d4d8cf1dd8c6e1": (
        "Mazda Autozam blue kei car sealed blister listing",
        ["condition_noise", "seller_wrapper"],
        "mazda auto zam tiny coupe",
        ["spacing", "marketplace_wrapper"],
    ),
    "fandom-family-fd96307f2dc8b421": (
        "Custom '53 Chevy red Hot Wheels loose seller lot",
        ["condition_noise", "seller_wrapper"],
        "custm 53 chevy pickup model",
        ["misspelling", "marketplace_wrapper"],
    ),
}

MERGE_QUERIES: dict[str, tuple[str, list[str]]] = {
    "fandom-family-04829924a36830a6": (
        "Purple Passion hot rod dark blue sealed toy",
        ["condition_noise", "marketplace_wrapper"],
    ),
    "fandom-family-6062af64f2e5a66c": (
        "Tesla Plaid Model S red Hot Wheels loose",
        ["condition_noise", "spacing"],
    ),
    "fandom-family-aa499ddb791c6991": (
        "67 C10 Chevy pickup orange collector lot",
        ["marketplace_wrapper", "spacing"],
    ),
    "fandom-family-b60363832032d566": (
        "Subaru BRZ blue carded import diecast",
        ["condition_noise", "seller_wrapper"],
    ),
}

HOLD_QUERIES: dict[str, tuple[str, list[str]]] = {
    "fandom-family-089ff8645b5f2de7": (
        "55 Chevy orange loose mystery casting",
        ["identity_ambiguity", "seller_wrapper"],
    ),
    "fandom-family-0e07a7139454d2e8": (
        "BNR 32 Nissan Skyline GTR red collector car",
        ["identity_ambiguity", "spacing"],
    ),
    "fandom-family-369b0be5855c0a1c": (
        "LBWK Nissan Skyline 2000 GTR blue short card",
        ["condition_noise", "identity_ambiguity"],
    ),
    "fandom-family-4f9ee66afdfe8cac": (
        "Power Wheels Dune Racer orange diecast listing",
        ["identity_ambiguity", "marketplace_wrapper"],
    ),
    "fandom-family-8403e21a29c27eab": (
        "Mario Standard Kart loose Hot Wheels vehicle",
        ["identity_ambiguity", "series_noise"],
    ),
    "fandom-family-8d24c626a51b1804": (
        "Batman Robin Batmobile black red carded car",
        ["condition_noise", "identity_ambiguity"],
    ),
    "fandom-family-c639dc688e21d33b": (
        "Mazda Miata MX5 roadster 2025 diecast",
        ["identity_ambiguity", "year_noise"],
    ),
}

UNRELATED_QUERIES = [
    "juxaprenoid",
    "klyzomareth",
    "nexuvandrix",
    "phyrqotulon",
    "plaxumdrith",
    "qevornyxal",
    "trazuphelix",
    "vortiqsable",
    "wexorinblath",
    "zxqvornelith",
]


def _load_builder():
    path = ROOT / "scripts/build_family_retrieval_benchmark.py"
    spec = importlib.util.spec_from_file_location("family_retrieval_benchmark", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load family-retrieval benchmark contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_query_pack() -> tuple[dict[str, Any], Any]:
    contract = _load_builder()
    registry = contract._load(DATA / "review_family_registry.json")
    projection = contract._load(DATA / "review_family_knowledge.json")
    human = contract._load(DATA / "human_backed_catalog.json")
    expected_positive = {item["review_family_id"] for item in registry["new_families"]}
    expected_merge = {item["source_family_review_id"] for item in registry["merge_links"]}
    expected_hold = {item["review_family_id"] for item in registry["hold_exclusions"]}
    if set(POSITIVE_QUERIES) != expected_positive:
        raise ValueError("authored positive-query identities differ from the registry")
    if set(MERGE_QUERIES) != expected_merge:
        raise ValueError("authored merge-query identities differ from the registry")
    if set(HOLD_QUERIES) != expected_hold:
        raise ValueError("authored hold-query identities differ from the registry")

    common = {
        "authored_at": AUTHORED_AT,
        "authored_by": "evaluation_query_author",
        "authoring_method": contract.AUTHORING_POLICY["method"],
        "retriever_output_viewed": False,
        "split": "test",
    }
    cases: list[dict[str, Any]] = []
    for family_id, values in POSITIVE_QUERIES.items():
        market_query, market_tags, lexical_query, lexical_tags = values
        suffix = family_id.removeprefix("fandom-family-")
        reference = {"kind": "review_family", "review_family_id": family_id}
        group = f"review:{family_id}"
        cases.extend(
            [
                {
                    **common,
                    "case_id": f"fre-positive-{suffix}-marketplace",
                    "case_type": "positive_family",
                    "casting_group_id": group,
                    "challenge_style": "marketplace_noise",
                    "noise_tags": market_tags,
                    "query_text": market_query,
                    "review_reference": reference,
                },
                {
                    **common,
                    "case_id": f"fre-positive-{suffix}-lexical",
                    "case_type": "positive_family",
                    "casting_group_id": group,
                    "challenge_style": "lexical_variation",
                    "noise_tags": lexical_tags,
                    "query_text": lexical_query,
                    "review_reference": reference,
                },
            ]
        )
    for family_id, (query, tags) in MERGE_QUERIES.items():
        suffix = family_id.removeprefix("fandom-family-")
        cases.append(
            {
                **common,
                "case_id": f"fre-merge-{suffix}",
                "case_type": "merge_control",
                "casting_group_id": f"merge:{family_id}",
                "challenge_style": "merge_existing_family",
                "noise_tags": tags,
                "query_text": query,
                "review_reference": {
                    "kind": "merge_control",
                    "source_family_review_id": family_id,
                },
            }
        )
    for family_id, (query, tags) in HOLD_QUERIES.items():
        suffix = family_id.removeprefix("fandom-family-")
        cases.append(
            {
                **common,
                "case_id": f"fre-hold-{suffix}",
                "case_type": "hold_control",
                "casting_group_id": f"hold:{family_id}",
                "challenge_style": "held_identity",
                "noise_tags": tags,
                "query_text": query,
                "review_reference": {
                    "kind": "hold_control",
                    "review_family_id": family_id,
                },
            }
        )
    for index, query in enumerate(UNRELATED_QUERIES):
        control_id = f"zero-overlap-{index:02d}"
        cases.append(
            {
                **common,
                "case_id": f"fre-unrelated-{index:02d}",
                "case_type": "unrelated_control",
                "casting_group_id": f"unrelated:{control_id}",
                "challenge_style": "no_overlap",
                "noise_tags": ["no_overlap"],
                "query_text": query,
                "review_reference": {
                    "control_id": control_id,
                    "kind": "unrelated_control",
                },
            }
        )

    sut = contract._system_under_test(
        human_path=DATA / "human_backed_catalog.json",
        projection_path=DATA / "review_family_knowledge.json",
    )
    payload = {
        "authorship_policy": contract.AUTHORING_POLICY,
        "benchmark_version": contract.BENCHMARK_VERSION,
        "cases": sorted(cases, key=lambda item: item["case_id"]),
        "eligible_for": contract.ELIGIBLE_FOR,
        "excluded_from": contract.EXCLUDED_FROM,
        "expected_counts": contract.EXPECTED_CASE_COUNTS,
        "query_pack_version": contract.QUERY_PACK_VERSION,
        "schema_version": contract.QUERY_PACK_SCHEMA,
        "split": "test",
        "status": "pending_owner_review",
        "system_under_test": sut,
    }
    contract.validate_query_pack(
        payload,
        registry=registry,
        projection=projection,
        human=human,
        system_under_test=sut,
    )
    return payload, contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        payload, contract = build_query_pack()
        expected = contract._stable_json(payload)
        if arguments.check:
            contract._check_text(arguments.output, expected)
            print("family retrieval query pack is reproducible")
        else:
            contract._atomic_write(arguments.output, expected)
            print(f"wrote {arguments.output}")
        return 0
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
