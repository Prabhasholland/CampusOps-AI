import pickle
import re
from pathlib import Path
from typing import List, Optional

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .base import Hit
from .chunker import Chunk

INDEX_DIR = Path(__file__).resolve().parent.parent.parent / "kb" / ".index"

# Word-boundary tokenization splits "gferis@nust.na" into "gferis", "nust",
# "na" - so a chunk with a dozen @nust.na addresses racks up "nust" far more
# than a chunk that just mentions NUST in prose, and wins queries it has no
# real business winning. Mask contact details out of the text used for
# matching (never out of chunk.text itself, which is what's actually sent
# to CALL-E) so a directory-style KB file can't out-vote relevant prose on
# term frequency alone.
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"\+?\d[\d ]{6,}\d")


def _mask_contact_details(text: str) -> str:
    return _PHONE_RE.sub(" ", _EMAIL_RE.sub(" ", text))


# No stemming means "bachelors" (how a caller says it) and "Bachelor" (how
# every KB entry writes it) are unrelated tokens - found when "bachelors of
# economics" scored the actual Bachelor of Economics entry below threshold
# and matched a chunk that only mentions "Economics" as an elective subject
# option elsewhere. This is a light, deliberately conservative suffix strip,
# not a real stemmer (no NLTK - scikit-learn only, per docs/retrieval-spec.md)
# - it only trims plain plural/possessive "s", not derivational endings.
_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")


def _light_stem(word: str) -> str:
    if word.endswith("'s"):
        word = word[:-2]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("es") and word[-3] in "sxz":
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


# A single recurring pattern kept breaking retrieval, in three different
# files, at three different sizes, sometimes even after email/phone
# masking: a chunk that's structurally repetitive - a directory listing,
# a repeated page header, a satellite-campus paragraph mentioning the same
# place name three times - packs enough raw repetition into one chunk to
# outscore genuinely relevant chunks, because sublinear_tf still rewards
# going from 1 occurrence to 4+. Capping how many times any one token can
# count per chunk is a general fix for the pattern itself, rather than
# excluding one more file every time a new instance of it turns up.
_MAX_TOKEN_REPEATS_PER_CHUNK = 3


def _stem_tokenize(text: str) -> List[str]:
    # Stop words are filtered here, before stemming, rather than left to
    # TfidfVectorizer's own stop_words= step - that step matches against
    # unstemmed forms, so stemmed words like "alway" (from "always") would
    # silently stop being recognised as stop words at all.
    tokens = _TOKEN_RE.findall(text.lower())
    stemmed = [_light_stem(t) for t in tokens if t not in ENGLISH_STOP_WORDS]
    counts: dict = {}
    capped = []
    for tok in stemmed:
        counts[tok] = counts.get(tok, 0) + 1
        if counts[tok] <= _MAX_TOKEN_REPEATS_PER_CHUNK:
            capped.append(tok)
    return capped


class TfidfRetriever:
    def __init__(self) -> None:
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.chunks: List[Chunk] = []

    def build(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        if not chunks:
            self.vectorizer = None
            self.matrix = None
            return
        corpus = [_mask_contact_details(f"{c.heading}\n{c.text}") for c in chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
            tokenizer=_stem_tokenize,
            token_pattern=None,
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, k: int = 4) -> List[Hit]:
        if self.vectorizer is None or self.matrix is None:
            return []
        q = self.vectorizer.transform([_mask_contact_details(query)])
        scores = linear_kernel(q, self.matrix).flatten()
        top = scores.argsort()[::-1][:k]
        return [Hit(chunk=self.chunks[i], score=float(scores[i])) for i in top if scores[i] > 0]

    def save(self, tenant: str) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        with open(INDEX_DIR / f"{tenant}.pkl", "wb") as f:
            pickle.dump(
                {"vectorizer": self.vectorizer, "matrix": self.matrix, "chunks": self.chunks}, f
            )

    @classmethod
    def load(cls, tenant: str) -> Optional["TfidfRetriever"]:
        path = INDEX_DIR / f"{tenant}.pkl"
        if not path.exists():
            return None
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.vectorizer = data["vectorizer"]
        inst.matrix = data["matrix"]
        inst.chunks = data["chunks"]
        return inst
