"""Industry groups — the top-level way a user chooses their workspace.

Each pack declares an `industry` key that maps into one of these groups. The
frontend hub renders one card per industry; picking one scopes the workspace to
just that industry's document types.
"""

from __future__ import annotations

# key -> {label, icon (lucide), tagline}
INDUSTRIES = {
    "finance": {
        "label": "Finance & Accounting",
        "icon": "Landmark",
        "tagline": "Invoices, receipts, expenses and tax — reconciled and fraud-checked.",
    },
    "banking": {
        "label": "Banking & Lending",
        "icon": "Banknote",
        "tagline": "Statements, pay stubs and loan files — verified for underwriting.",
    },
    "insurance_health": {
        "label": "Insurance & Healthcare",
        "icon": "HeartPulse",
        "tagline": "Claims, medical bills and prescriptions — duplicate- and limit-checked.",
    },
    "hr": {
        "label": "HR & Recruiting",
        "icon": "Users",
        "tagline": "Résumés, offers and certificates — matched and consistency-checked.",
    },
    "identity": {
        "label": "Identity & KYC",
        "icon": "ShieldCheck",
        "tagline": "IDs and proof-of-address — checksums, expiry and authenticity signals.",
    },
    "legal": {
        "label": "Legal & Real Estate",
        "icon": "Scale",
        "tagline": "Contracts, NDAs and leases — clauses, parties and term-date logic.",
    },
    "logistics": {
        "label": "Logistics & Trade",
        "icon": "Truck",
        "tagline": "POs, bills of lading and customs — quantity and consistency matched.",
    },
    "academic": {
        "label": "Education & Academic",
        "icon": "GraduationCap",
        "tagline": "Transcripts and mark sheets — totals and credential verification.",
    },
}
