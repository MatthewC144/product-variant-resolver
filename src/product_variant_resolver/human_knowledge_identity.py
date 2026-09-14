"""Isolated v4 identity admission and exact, budgeted form-posting retrieval."""
from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from typing import Any
from uuid import UUID

from .human_knowledge import (
    CharacterIndexMetadata,
    HumanKnowledgeCandidate,
    HumanKnowledgeCatalog,
    HumanKnowledgeDocument,
)
from .identity import normalize_text
from .retrieval import HashingEmbedding
from .schemas import ExtractedSignals

VERSION = "human-knowledge-hybrid-v4"
INDEX_VERSION = "human-knowledge-identity-postings-v1"
PROTOCOL_SHA256 = "31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde"
MANIFEST_SHA256 = "b7634f7f3d52277c4ee4d92489b656fcf1a6c446d56085c5affb7cb7a12c6ea7"
ALLOWED_FIELDS = {"provisional_variant": ["casting"], "review_family": ["casting", "aliases"]}
NOISE = frozenset("""as blister black blue box boxed cabinet carded car case collectible collector
diecast display estate find from gray green grey hot hotwheels in item light local loose maker
miniature missing model new orange outer package pack piece pictured pickup protective purple red
scale sealed shelf silver small sold storage the toy unopened unknown vehicle wear wheels white
with yellow""".split())


@dataclass(frozen=True, slots=True)
class IdentityCorePolicy:
    version: str = "identity-core-policy-v1"
    noise_tokens: frozenset[str] = NOISE

    def core(self, text: str) -> str:
        return " ".join(token for token in normalize_text(text).split() if token not in self.noise_tokens)


@dataclass(frozen=True, slots=True)
class IdentityLimits:
    query_characters: int = 512
    query_tokens_before_noise: int = 64
    identity_forms_per_document: int = 32
    query_forms: int = 256
    posting_entries_per_query: int = 1_000_000
    source_candidates: int = 25
    dense_union: int = 50

    def __post_init__(self) -> None:
        if any(type(value) is not int or value < 1 for value in asdict(self).values()):
            raise ValueError("identity limits must be positive integers")


@dataclass(frozen=True, slots=True)
class HumanKnowledgeV4Config:
    character_score_floor: float
    character_rrf_weight: float
    artifact_version: str = "human-knowledge-retrieval-v4-experimental"
    artifact_sha256: str = "unselected"
    protocol_sha256: str = PROTOCOL_SHA256
    limits: IdentityLimits = field(default_factory=IdentityLimits)

    def __post_init__(self) -> None:
        if (type(self.character_score_floor) not in {int, float}
                or type(self.character_rrf_weight) not in {int, float}
                or not math.isfinite(self.character_score_floor)
                or self.character_score_floor not in {0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55}
                or not math.isfinite(self.character_rrf_weight)
                or self.character_rrf_weight not in {0.5, 1.0, 1.5}
                or self.protocol_sha256 != PROTOCOL_SHA256):
            raise ValueError("v4 configuration differs from frozen protocol")


@dataclass(frozen=True, slots=True)
class IdentityRetrievalWork:
    policy_version: str = "identity-core-policy-v1"
    query_forms: int = 0
    posting_entries_visited: int = 0
    scored_forms: int = 0
    exact_candidates: int = 0
    character_candidates: int = 0
    dense_union: int = 0
    abstention_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _IdentityForm:
    form_id: str
    document_uuid: UUID
    mode: str
    text: str
    core_tokens: frozenset[str]
    weights: dict[str, float]


def grams(text: str) -> Counter[str]:
    return Counter(text[index:index + size] for size in (2, 3)
                   for index in range(max(0, len(text) - size + 1)))


class IdentityPostingIndex:
    def __init__(self, documents: tuple[HumanKnowledgeDocument, ...],
                 policy: IdentityCorePolicy | None = None, limits: IdentityLimits | None = None):
        self.policy = policy or IdentityCorePolicy()
        self.limits = limits or IdentityLimits()
        self.documents = {item.knowledge_uuid: item for item in documents}
        if not documents or len(self.documents) != len(documents):
            raise ValueError("identity index requires nonempty, unique document UUIDs")
        if len({item.knowledge_id for item in documents}) != len(documents):
            raise ValueError("identity index requires unique knowledge IDs")
        raw: dict[str, tuple[UUID, str, str, frozenset[str], Counter[str]]] = {}
        document_grams: dict[UUID, set[tuple[str, str]]] = {}
        document_tokens: dict[UUID, set[str]] = {}
        self.identity_lengths: set[int] = set()
        for item_uuid, document in sorted(self.documents.items(), key=lambda pair: str(pair[0])):
            values = ((document.casting,) if document.knowledge_type == "provisional_variant"
                      else (document.casting, *getattr(document, "aliases")))
            seen: set[tuple[str, str]] = set()
            document_grams[item_uuid] = set()
            document_tokens[item_uuid] = set()
            for value in values:
                core = self.policy.core(value)
                if not core:
                    raise ValueError("identity core normalizes to empty")
                tokens = frozenset(core.split())
                self.identity_lengths.add(len(core.split()))
                document_tokens[item_uuid].update(tokens)
                for mode, text in (("spaced", core), ("compact", core.replace(" ", ""))):
                    if (mode, text) in seen:
                        continue
                    seen.add((mode, text))
                    counts = grams(text)
                    if not counts:
                        raise ValueError("identity core is too short for grams")
                    form_id = hashlib.sha256(f"{item_uuid}\x1f{mode}\x1f{text}".encode()).hexdigest()
                    raw[form_id] = (item_uuid, mode, text, tokens, counts)
                    document_grams[item_uuid].update((mode, gram) for gram in counts)
            if len(seen) > self.limits.identity_forms_per_document:
                raise ValueError("identity form limit exceeded")
        count = len(documents)
        df = Counter(key for keys in document_grams.values() for key in keys)
        self.idf = {key: math.log((count + 1) / (frequency + 1)) + 1
                    for key, frequency in df.items()}
        self.unknown_idf = math.log(count + 1) + 1
        token_df = Counter(token for tokens in document_tokens.values() for token in tokens)
        self.token_idf = {token: math.log((count + 1) / (frequency + 1)) + 1
                          for token, frequency in token_df.items()}
        self.document_tokens = document_tokens
        self.forms: dict[str, _IdentityForm] = {}
        postings: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
        token_postings: dict[str, set[str]] = defaultdict(set)
        for form_id, (item_uuid, mode, text, tokens, counts) in sorted(raw.items()):
            weighted = {gram: frequency * self.idf[(mode, gram)] for gram, frequency in sorted(counts.items())}
            norm = math.sqrt(sum(value * value for value in weighted.values()))
            normalized = {gram: value / norm for gram, value in weighted.items()}
            if not all(math.isfinite(value) for value in normalized.values()):
                raise ValueError("identity index has nonfinite weights")
            self.forms[form_id] = _IdentityForm(form_id, item_uuid, mode, text, tokens, normalized)
            for gram, weight in normalized.items():
                postings[(mode, gram)].append((form_id, weight))
            if mode == "spaced":
                for token in tokens:
                    token_postings[token].add(form_id)
        self.postings = {key: tuple(entries) for key, entries in sorted(postings.items())}
        self.token_postings = {token: tuple(sorted(ids)) for token, ids in token_postings.items()}
        self.metadata = CharacterIndexMetadata(
            INDEX_VERSION, count, len(self.postings), sum(len(entries) for entries in self.postings.values()),
            (2, 3), ("spaced", "compact"), 1, "knowledge_uuid", ALLOWED_FIELDS)

    def query_forms(self, text: str) -> tuple[list[tuple[str, str]], str | None]:
        normalized = normalize_text(text)
        if (len(normalized) > self.limits.query_characters
                or len(normalized.split()) > self.limits.query_tokens_before_noise):
            return [], "query_limit"
        tokens = self.policy.core(text).split()
        if not tokens:
            return [], "noise_only"
        forms: set[tuple[str, str]] = set()
        for length in sorted(self.identity_lengths):
            for size in range(max(1, length - 1), length + 2):
                for start in range(max(0, len(tokens) - size + 1)):
                    spaced = " ".join(tokens[start:start + size])
                    forms.update((("spaced", spaced), ("compact", spaced.replace(" ", ""))))
                    if len(forms) > self.limits.query_forms:
                        return sorted(forms), "window_limit"
        return sorted(forms), None

    def exact_scores(self, query: str) -> dict[UUID, float]:
        tokens = set(self.policy.core(query).split())
        form_ids = {form_id for token in tokens for form_id in self.token_postings.get(token, ())}
        scores: dict[UUID, float] = {}
        for form_id in sorted(form_ids):
            form = self.forms[form_id]
            if form.core_tokens <= tokens:
                score = sum(self.token_idf[token] for token in sorted(form.core_tokens))
                scores[form.document_uuid] = max(scores.get(form.document_uuid, 0), score)
        return scores

    def rank_with_work(self, query: str, *, score_floor: float) -> tuple[list[tuple[HumanKnowledgeDocument, float]], IdentityRetrievalWork]:
        if not math.isfinite(score_floor) or not 0 < score_floor <= 1:
            raise ValueError("character floor must be finite in (0,1]")
        query_forms, reason = self.query_forms(query)
        work = IdentityRetrievalWork(query_forms=len(query_forms), abstention_reason=reason)
        if reason:
            return [], work
        visits = 0
        scored: set[str] = set()
        scores: dict[UUID, float] = {}
        for mode, text in query_forms:
            weighted = {gram: frequency * self.idf.get((mode, gram), self.unknown_idf)
                        for gram, frequency in sorted(grams(text).items())}
            norm = math.sqrt(sum(value * value for value in weighted.values()))
            if norm == 0:
                continue
            dots: dict[str, float] = defaultdict(float)
            for gram, value in weighted.items():
                for form_id, posting_weight in self.postings.get((mode, gram), ()):
                    if visits >= self.limits.posting_entries_per_query:
                        return [], replace(work, posting_entries_visited=visits,
                                           scored_forms=len(scored), abstention_reason="posting_limit")
                    visits += 1
                    scored.add(form_id)
                    dots[form_id] += (value / norm) * posting_weight
            for form_id, score in dots.items():
                if not math.isfinite(score):
                    raise ValueError("identity index produced nonfinite score")
                item_uuid = self.forms[form_id].document_uuid
                scores[item_uuid] = max(scores.get(item_uuid, 0), score)
        ranked = sorted(((self.documents[item_uuid], score) for item_uuid, score in scores.items()
                         if score >= score_floor), key=lambda pair: (-pair[1], str(pair[0].knowledge_uuid)))
        return ranked, replace(work, posting_entries_visited=visits, scored_forms=len(scored))


class HumanKnowledgeIdentityRetriever:
    version = VERSION

    def __init__(self, catalog: HumanKnowledgeCatalog, embedding: HashingEmbedding,
                 config: HumanKnowledgeV4Config):
        if embedding.dimensions != 192:
            raise ValueError("v4 requires frozen 192-dimensional hashing")
        self.catalog, self.embedding, self.config = catalog, embedding, config
        self.artifact_version, self.artifact_sha256 = config.artifact_version, config.artifact_sha256
        self.character_index = IdentityPostingIndex(catalog.documents, limits=config.limits)
        self._vectors = {item.knowledge_uuid: embedding.encode(item.searchable_text) for item in catalog.documents}

    @property
    def character_index_metadata(self) -> dict[str, Any]:
        return {**self.character_index.metadata.as_dict(), "form_count": len(self.character_index.forms),
                "posting_definition": "normalized_form_gram_entries"}

    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[HumanKnowledgeCandidate]:
        return self.retrieve_with_work(signals, limit)[0]

    def retrieve_with_work(self, signals: ExtractedSignals, limit: int) -> tuple[list[HumanKnowledgeCandidate], IdentityRetrievalWork]:
        if not 1 <= limit <= 25:
            raise ValueError("human knowledge limit must be between 1 and 25")
        index, config = self.character_index, self.config
        query = signals.normalized_title
        character, work = index.rank_with_work(query, score_floor=config.character_score_floor)
        if work.abstention_reason:
            return [], work
        sparse_scores = index.exact_scores(query)
        sparse_ids = sorted(sparse_scores, key=lambda item: (-sparse_scores[item], str(item)))[:config.limits.source_candidates]
        character = character[:config.limits.source_candidates]
        character_scores = {item.knowledge_uuid: score for item, score in character}
        union = sorted(set(sparse_ids) | set(character_scores), key=str)
        if len(union) > config.limits.dense_union:
            raise ValueError("identity dense union exceeded frozen bound")
        work = replace(work, exact_candidates=len(sparse_ids), character_candidates=len(character), dense_union=len(union))
        if not union:
            return [], work
        query_vector = self.embedding.encode(query)
        dense_scores = {item: sum(a * b for a, b in zip(query_vector, self._vectors[item], strict=True)) for item in union}
        if not all(math.isfinite(value) for value in dense_scores.values()):
            raise ValueError("identity dense scores are nonfinite")
        dense_ids = sorted(union, key=lambda item: (-dense_scores[item], str(item)))
        sparse_ranks = {item: rank for rank, item in enumerate(sparse_ids, 1)}
        dense_ranks = {item: rank for rank, item in enumerate(dense_ids, 1)}
        character_ranks = {item.knowledge_uuid: rank for rank, (item, _) in enumerate(character, 1)}
        fused = {item: sum(weight / (60 + ranks[item]) for weight, ranks in
                           ((1, sparse_ranks), (1, dense_ranks), (config.character_rrf_weight, character_ranks))
                           if item in ranks) for item in union}
        ordered = sorted(union, key=lambda item: (-fused[item], str(item)))[:limit]
        tokens = set(index.policy.core(query).split())
        return [HumanKnowledgeCandidate(
            index.documents[item], sparse_ranks.get(item), sparse_scores.get(item) if item in sparse_ranks else None,
            dense_ranks[item], dense_scores[item], rank, fused[item],
            tuple(sorted(tokens & index.document_tokens[item])), character_ranks.get(item), character_scores.get(item))
            for rank, item in enumerate(ordered, 1)], work
