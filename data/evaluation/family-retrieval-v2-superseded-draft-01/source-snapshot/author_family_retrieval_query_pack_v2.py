#!/usr/bin/env python3
"""Explicitly composed final-v2 questions; no retrieval, automatic mutation or labels."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.family_retrieval_final_v2 import check, freeze  # noqa: E402

# Each pair: marketplace title / lexical variation. Written after committed winner,
# without executing/viewing any of these new questions' retrieval outputs.
POSITIVE = {
    "0573861db69878eb": ("Rear blister dent on blue Max Steel from weekend swap table", "maxstiel fantasy racer wanted"),
    "08cb7fadb9fed12d": ("Seller found 1988 Jeep Wagoneer under an old display stand", "jeep wagonear eighty eight casting"),
    "1555c05ceeb491cb": ("Silver 94 Audi Avant RS2 with price sticker across front window", "audi rs-two avante 1994 estate"),
    "174efb9bce3a441e": ("Dusty orange Lamborghini Huracan Sterrato photographed beside its blister", "lmborghini huracn sterratto offroader"),
    "18e55e067083dbd1": ("87 Audi quattro has a bent hanger tab and silver paint flecks", "audy quatrro eighty-seven rally miniature"),
    "1b2a4227b4e5decd": ("Seller bundles black Mercedes Benz 500 E with an empty acrylic stand", "mercedez five-hundred-E saloon"),
    "2357e7eb6b4e62b8": ("Pink Monster High Ghoul Mobile shown outside packaging on a cloth", "ghoul mobil from monster high"),
    "356e4ef63275a661": ("Green Fish'd & Chip'd with shelf dust and a crumpled price tag", "fishd and chipd novelty casting"),
    "39b248ce2f3723cd": ("Twin Mill Gen-E silver paint photographed on the seller's desk", "twinmil gen-ee electric concept"),
    "3c9f928f085efaae": ("Kick Kart yellow fantasy racer with shop stamp on cardboard back", "kickkart kart racer miniature"),
    "440103f8ef3c6b70": ("Haulerback purple truck pulled from a dusty cabinet after moving house", "hawlerback hauler casting"),
    "45af5b93f3f6650f": ("Gold Custom Cadillac Fleetwood has rubbed corners on its backing card", "cust Cadillac Fleetwod lowrider"),
    "4bf5341a133d433b": ("Teal Hirohata Merc with scratched blister offered at a toy swap", "hirohata merck custom coupe"),
    "4d00e96d12341b4d": ("Orange Nerve Hammer pictured with a torn receipt beneath the stand", "nervehamer fantasy hammer car"),
    "4d2de6db3d5bba63": ("Red Crescendo music car in a cloudy blister with faded shop sticker", "crecsendo music inspired casting"),
    "526b697937fde7cc": ("80 El Camino black pickup from garage collection; hanger tab creased", "1980 el camno pickup casting"),
    "57cf5c31afbadc57": ("Green The Vanster with loose axle photographed at a flea-market stall", "the vansterr fantasy van"),
    "59e5682e50af879e": ("White Proton Saga from storage tub; paint has a tiny roof chip", "proton sagga malaysian saloon"),
    "7e221ec8ecd02815": ("Tan X-34 Landspeeder Star Wars toy beside a handwritten price label", "x thirty-four landspeeder vehicle"),
    "85226ac5ac0d3f77": ("Yellow Fiat 500e has crushed packaging near the lower right corner", "fiat 500 ee electric hatchback"),
    "85e407525ac7bf41": ("Blue Small Bloc with rubbed roof; seller cannot locate original blister", "smal bloc fantasy smallblock"),
    "89930c384be2e8bf": ("Red Kowloon'd Hypervan from display cabinet; price sticker left on back", "kowloond hyper-van custom van"),
    "8a07157f2af2ddd5": ("Bogzilla green creature racer shown next to a cracked protective case", "bogzillla monster racer miniature"),
    "8cce01fa7d44112a": ("Purple Deora III with a shop security label covering the collector art", "deorra iii surf concept"),
    "9069156ec909a92e": ("Pink Donut Drifter with bent card edges photographed on a kitchen cloth", "doughnut drifter pastry car"),
    "99200212d1475ef2": ("2020 Ram 1500 Rebel pickup from seller's cabinet; dusty but boxed", "2020 ram 15 hundred rebel truck"),
    "a1b198f7d235f778": ("White Ford Performance SuperVan 4 offered with a damaged acrylic stand", "ford performance supervn iv racer"),
    "a2097eead3bd8db9": ("66 Buick Riviera teal paint under cloudy blister; seller notes shelf wear", "1966 buick riviera coupe miniature"),
    "a8e0dec4abdc4131": ("Silver DMC DeLorean found in moving cartons with no paper receipt", "dmc de-lorien stainless coupe"),
    "aab5350cb90d72ed": ("21 Ford Bronco blue off-road toy photographed with wrinkled price label", "ford brnoco twenty-one SUV"),
    "aaafff57ac4d4daa": ("Red Morgan Super 3 sits on an unmarked stand; rear blister is split", "morgan supr 3 three-wheeler"),
    "aec11693bfe04245": ("Mazda REPU orange rotary pickup displayed beside its torn backing card", "mazda rep-u rotary pickup casting"),
    "b31d285560d8a242": ("Grey Ford Mustang GTD from a toy swap; scratched clear plastic cover", "mustangg gtd ford track coupe"),
    "b3cd4f5a5f7e196a": ("69 Corvette Racer yellow paint with old shop sticker still attached", "1969 corvette racr competition car"),
    "c655fb5244c584ae": ("Red Kei Swap parked on seller's desk; backing card folded at top", "kei swapp modified microtruck"),
    "d114c33db6fa215b": ("90 Honda Civic EF white hatchback pictured beside a crumpled shop bag", "honda civik e-f from ninety"),
    "d5c83bb87be8cab0": ("Chrome Super Twin Mill has dusty packaging and a faded price sticker", "super twinmill twin engine fantasy"),
    "d816204cf649a0c0": ("Black Draftnator with wrinkled backing card and no original sales receipt", "draftinator drafting racer miniature"),
    "d90841788b1d98a2": ("Blue Alpha Pursuit patrol car has a scratch along its clear blister", "alpha persuit police casting"),
    "db3fe3a0103099ec": ("22 Ford Maverick Custom red truck photographed beside a damaged stand", "2022 ford maverik cust pickup"),
    "e7d4d8cf1dd8c6e1": ("Blue Mazda Autozam removed from an old cabinet; seller reports roof rub", "mazda autozamm kei coupe"),
    "fd96307f2dc8b421": ("Custom 53 Chevy red pickup found in garage carton with torn price tag", "custom chevie fifty-three pickup"),
}
MERGE = {
    "04829924a36830a6": "Purple Passion blue hot rod photographed beside an empty display plinth",
    "6062af64f2e5a66c": "Tesla Model S Plaid red saloon with sticker residue on the windshield",
    "aa499ddb791c6991": "Chevy C10 from 1967 with orange paint and a creased hanger tab",
    "b60363832032d566": "Subaru BRZ blue coupe found in garage cartons with scratched blister",
}
HOLD = {
    "089ff8645b5f2de7": "Chevrolet fifty-five casting; seller unsure which original tool this is",
    "0e07a7139454d2e8": "Nissan Skyline GT-R R32 labelled BNR32; base stamp not photographed",
    "369b0be5855c0a1c": "Liberty Walk Nissan Skyline 2000 GT-R without a readable base stamp",
    "4f9ee66afdfe8cac": "Power Wheels Dune Racer miniature beside a handwritten garage-sale tag",
    "8403e21a29c27eab": "Standard Kart with Mario markings; chassis version absent from listing",
    "8d24c626a51b1804": "Batman and Robin Batmobile; seller gives no movie/tool lineage information",
    "c639dc688e21d33b": "MX-5 Mazda Miata offered without generation or tooling description",
}
# Ordinary non-vehicle terms, not machine-picked for a low retrieval score.
UNRELATED = ["quinoa", "origami", "sourdough", "percolator", "ukulele", "tapestry",
    "metronome", "stethoscope", "embroidery", "thermocouple"]


def authored_cases() -> list[dict]:
    cases = []
    for suffix, pair in POSITIVE.items():
        for style, query in zip(("marketplace_noise", "lexical_variation"), pair, strict=True):
            cases.append({"case_id": f"fr2-positive-{suffix}-{style}", "case_type": "positive_family",
                "challenge_style": style, "query_text": query,
                "review_reference": {"kind": "review_family", "review_family_id": f"fandom-family-{suffix}"}})
    for kind, mapping, style in (("merge", MERGE, "merge_existing_family"), ("hold", HOLD, "held_identity")):
        for suffix, query in mapping.items():
            cases.append({"case_id": f"fr2-{kind}-{suffix}", "case_type": f"{kind}_control",
                "challenge_style": style, "query_text": query,
                "review_reference": {"kind": f"{kind}_control", "review_family_id": f"fandom-family-{suffix}"}})
    for number, query in enumerate(UNRELATED):
        cases.append({"case_id": f"fr2-unrelated-{number:02d}", "case_type": "unrelated_control",
            "challenge_style": "no_overlap", "query_text": query,
            "review_reference": {"kind": "unrelated_control", "control_id": f"nonvehicle-{number:02d}"}})
    return sorted(cases, key=lambda case: case["case_id"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check(authored_cases())
    else:
        freeze(authored_cases())
    print("final-v2 queries frozen/validated; WAIT for owner approval; no labels/retrieval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
