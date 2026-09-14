"""T2 algorithm checks, not development selection or final-quality evidence."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import FrozenInstanceError, replace
from uuid import UUID

import pytest

from product_variant_resolver.human_knowledge import (
    HumanKnowledgeCatalog,
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
)
from product_variant_resolver.human_knowledge_identity import (
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
    IdentityCorePolicy,
    IdentityLimits,
    IdentityPostingIndex,
)
from product_variant_resolver.retrieval import HashingEmbedding
from product_variant_resolver.signals import extract_signals


def family(number: int, casting: str, aliases: tuple[str, ...] = ()) -> ReviewFamilyKnowledgeDocument:
    return ReviewFamilyKnowledgeDocument(
        review_family_uuid=UUID(int=number), review_family_id=f"family-{number}", brand="SecretBrand",
        casting=casting, aliases=aliases, source_record_ids=("source",),
        identity_status="family_accepted_variants_unreviewed",
    )


def retriever(documents=None, **limits):
    documents = documents or (family(2, "Alpha Coupe"), family(1, "Beta Sedan"))
    catalog = HumanKnowledgeCatalog("test", "test", list(documents))
    return HumanKnowledgeIdentityRetriever(catalog, HashingEmbedding(),
        HumanKnowledgeV4Config(.35, 1, limits=IdentityLimits(**limits)))


def oracle(index, query):
    """Independent all-form/all-window TF-IDF cosine; never reads weighted postings."""
    def counts(text):
        return Counter(text[i:i+n] for n in (2, 3) for i in range(len(text)-n+1))
    forms = list(index.forms.values())
    df = Counter(key for document in index.documents for key in {
        (form.mode, gram) for form in forms if form.document_uuid == document
        for gram in counts(form.text)
    })
    n = len(index.documents)
    def vector(mode, text):
        values = {gram: count * (math.log((n+1)/(df.get((mode, gram), 0)+1))+1)
                  for gram, count in counts(text).items()}
        norm = math.sqrt(sum(value**2 for value in values.values()))
        return {gram: value/norm for gram, value in values.items()} if norm else {}
    scores = {}
    windows, reason = index.query_forms(query)
    assert reason is None
    for form in forms:
        document_vector = vector(form.mode, form.text)
        score = max((sum(value * document_vector.get(gram, 0) for gram, value in vector(mode, text).items())
                     for mode, text in windows if mode == form.mode), default=0)
        scores[form.document_uuid] = max(scores.get(form.document_uuid, 0), score)
    return scores


@pytest.mark.parametrize("query", ["Alpha Coupe", "listing AlphaCoupe", "Alphx Coupx", "bé ta sedan", "zqxv"])
def test_postings_equal_independent_cosine(query):
    index = IdentityPostingIndex((family(1, "Alpha Coupe", ("AlphaCoupe",)), family(2, "Beta Sedan")))
    actual, work = index.rank_with_work(query, score_floor=.000001)
    expected = oracle(index, query)
    assert {item.knowledge_uuid: score for item, score in actual} == pytest.approx(
        {key: value for key, value in expected.items() if value >= .000001}, rel=1e-12, abs=1e-12)
    assert work.posting_entries_visited <= 1_000_000


def test_document_df_not_alias_form_df_and_unknown_grams_preserved():
    index = IdentityPostingIndex((family(1, "Alpha Coupe", ("AlphaCoupe", "Alpha Racer")), family(2, "Beta Sedan")))
    assert index.idf[("compact", "Al".lower())] == pytest.approx(math.log(3/2)+1)
    exact = dict((str(d.knowledge_uuid), s) for d, s in index.rank_with_work("Alpha Coupe", score_floor=.001)[0])
    edited = dict((str(d.knowledge_uuid), s) for d, s in index.rank_with_work("Alphx Coupx", score_floor=.001)[0])
    assert edited[str(UUID(int=1))] < exact[str(UUID(int=1))]


def test_full_core_token_admission_and_broad_brand_is_not_identity():
    index = retriever().character_index
    assert index.exact_scores("Coupe") == {}
    assert UUID(int=2) in index.exact_scores("listing Coupe Alpha pickup")
    assert index.exact_scores("SecretBrand") == {}
    assert "secretbrand" not in index.token_postings
    assert IdentityCorePolicy().core("RED car Alpha COUPE boxed") == "alpha coupe"


@pytest.mark.parametrize("query,reason", [("red car boxed", "noise_only"), ("x"*513, "query_limit"), ("red "*65, "query_limit")])
def test_query_abstention_is_complete(query, reason):
    candidates, work = retriever().retrieve_with_work(extract_signals(query), 5)
    assert candidates == [] and work.abstention_reason == reason and work.dense_union == 0


def test_window_and_posting_caps_discard_even_exact_candidates():
    for limits, reason in [({"query_forms": 1}, "window_limit"), ({"posting_entries_per_query": 1}, "posting_limit")]:
        candidates, work = retriever(**limits).retrieve_with_work(extract_signals("Alpha Coupe"), 5)
        assert candidates == [] and work.abstention_reason == reason
        assert work.exact_candidates == work.character_candidates == work.dense_union == 0


def test_posting_boundary_and_query_local_immutable_work():
    service = retriever()
    first, work = service.retrieve_with_work(extract_signals("Alpha Coupe"), 5)
    for delta, expected in [(0, None), (-1, "posting_limit")]:
        index = IdentityPostingIndex(tuple(service.catalog.documents), limits=replace(IdentityLimits(),
            posting_entries_per_query=work.posting_entries_visited+delta))
        assert index.rank_with_work("Alpha Coupe", score_floor=.35)[1].abstention_reason == expected
    _, empty = service.retrieve_with_work(extract_signals("red toy"), 5)
    assert work.posting_entries_visited > 0 and empty.posting_entries_visited == 0
    assert service.retrieve_with_work(extract_signals("Alpha Coupe"), 5) == (first, work)
    with pytest.raises(FrozenInstanceError):
        work.dense_union = 0


def test_stable_uuid_ties_and_rrf_arithmetic():
    documents = (family(3, "Alpha Coupe"), family(1, "Alpha Coupe"), family(2, "Alpha Coupe"))
    candidates, work = retriever(documents).retrieve_with_work(extract_signals("Alpha Coupe"), 5)
    assert [item.document.knowledge_uuid.int for item in candidates] == [1, 2, 3]
    for candidate in candidates:
        assert candidate.rrf_score == pytest.approx(sum(1/(60+rank) for rank in
            (candidate.sparse_rank, candidate.dense_rank, candidate.character_rank) if rank is not None))
    assert work.dense_union == 3


def test_sources_bounded_no_type_quota_and_dense_only_admitted_union():
    service = retriever(tuple(family(i, "Alpha Coupe") for i in range(1, 61)))
    candidates, work = service.retrieve_with_work(extract_signals("Alpha Coupe"), 25)
    assert len(candidates) == work.exact_candidates == work.character_candidates == work.dense_union == 25
    assert [item.document.knowledge_uuid.int for item in candidates] == list(range(1, 26))


@pytest.mark.parametrize("documents", [(), (family(1, "red toy"),), (family(1, "a"),),
    (family(1, "Alpha"), family(1, "Beta"))])
def test_invalid_index_fails_instead_of_dropping_forms(documents):
    with pytest.raises(ValueError):
        IdentityPostingIndex(documents)


def test_form_ceiling_and_configuration_fail_closed():
    with pytest.raises(ValueError):
        IdentityPostingIndex((family(1, "Alpha", tuple(f"Alias {i}" for i in range(20))),))
    for floor, weight in [(float("nan"), 1), (.36, 1), (.35, 2)]:
        with pytest.raises(ValueError):
            HumanKnowledgeV4Config(floor, weight)
    with pytest.raises(ValueError):
        HumanKnowledgeIdentityRetriever(retriever().catalog, HashingEmbedding(64), HumanKnowledgeV4Config(.35, 1))
    with pytest.raises(ValueError):
        IdentityLimits(query_forms=0)


def test_nonfinite_dense_scores_fail_not_publish():
    service = retriever()
    service._vectors[UUID(int=2)] = (float("nan"),) * 192
    with pytest.raises(ValueError):
        service.retrieve_with_work(extract_signals("Alpha Coupe"), 5)


def test_character_only_typo_has_no_fabricated_sparse_rank():
    candidates, _ = retriever().retrieve_with_work(extract_signals("Alphx Coupx"), 5)
    target = next(item for item in candidates if item.document.knowledge_uuid == UUID(int=2))
    assert target.sparse_rank is None and target.sparse_score is None
    assert target.character_rank == 1 and target.character_score >= .35
    assert target.rrf_score == pytest.approx(1/(60+target.dense_rank) + 1/(60+target.character_rank))


def test_provisional_labels_and_raw_names_do_not_become_identity_forms():
    variant = HumanVariantKnowledgeDocument(UUID(int=1), "casting-1", UUID(int=2), "variant-1",
        "Brand", "Alpha Coupe", "SecretSeries", "SecretVariant", "needs_canonical_review",
        ("SecretLabel",), ("SecretPricing",), ("SecretRaw",), ("case",))
    index = IdentityPostingIndex((variant,))
    assert {(form.mode, form.text) for form in index.forms.values()} == {
        ("spaced", "alpha coupe"), ("compact", "alphacoupe")}
    assert index.exact_scores("SecretLabel SecretRaw SecretPricing SecretSeries SecretVariant") == {}
