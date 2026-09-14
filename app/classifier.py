from dataclasses import dataclass
from typing import Optional

PROOF_OF_REG_KEYWORDS = [
    "proof of registration",
    "proof of reg",
    "registration letter",
    "confirmation of registration",
    "download my registration",
    "portal wont let me download",
    "portal won't let me download",
]

SUBJECT_CANCELLATION_KEYWORDS = ["cancel", "drop", "withdraw", "deregister", "unenroll"]

CATEGORY_KEYWORDS = {
    "fees": ["fee", "balance", "invoice", "payment", "pay "],
    "academic_records": ["transcript", "results", "marks", "grades"],
    "faculty": ["lecturer", "faculty", "department", "class"],
    "accommodation": ["accommodation", "res ", "residence", "hostel", "deposit"],
    "exams": ["exam", "test", "supplementary", "resit"],
    "it_support": ["portal", "login", "password", "wifi", "email account"],
}


@dataclass
class Classification:
    intent: str
    confidence: float
    category: Optional[str] = None


def classify(query: str) -> Classification:
    text = query.lower()

    if any(k in text for k in PROOF_OF_REG_KEYWORDS):
        return Classification("proof_of_registration", 0.9)

    if any(k in text for k in SUBJECT_CANCELLATION_KEYWORDS):
        return Classification("subject_cancellation", 0.85)

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return Classification("other", 0.6, category)

    return Classification("other", 0.4, "unclear")
