"""The domain library. Each pack is a declarative description; a few add small
deterministic custom checks. Adding a new domain = adding a pack to this file.
"""

from __future__ import annotations

from datetime import date
from typing import List

from schema import Check, Extraction

from .base import (
    ArithmeticRule,
    ColumnSpec,
    DomainPack,
    FieldSpec,
    SimilaritySpec,
    TableSpec,
    _parse_date,
)


# ---------------------------------------------------------------------------
# Custom deterministic checks (pure Python, no LLM)
# ---------------------------------------------------------------------------

def _id_checks(ext: Extraction) -> List[Check]:
    checks: List[Check] = []
    today = date.today()
    exp = _parse_date(ext.value("expiry_date"))
    if exp:
        ok = exp >= today
        checks.append(Check(rule="Document not expired", passed=ok,
                            reason=(f"Valid until {exp.isoformat()}." if ok
                                    else f"Expired on {exp.isoformat()}.")))
    dob = _parse_date(ext.value("date_of_birth"))
    if dob and dob >= today:
        checks.append(Check(rule="Date of birth sane", passed=False,
                            reason=f"Date of birth {dob.isoformat()} is not in the past."))
    return checks


def _contract_date_order(ext: Extraction) -> List[Check]:
    eff = _parse_date(ext.value("effective_date"))
    end = _parse_date(ext.value("end_date"))
    if eff and end:
        ok = end >= eff
        return [Check(rule="Term dates ordered", passed=ok,
                      reason=(f"Effective {eff.isoformat()} → ends {end.isoformat()}." if ok
                              else f"End date {end.isoformat()} precedes effective date {eff.isoformat()}."))]
    return []


def _bank_balance(ext: Extraction) -> List[Check]:
    opening = ext.number("opening_balance")
    closing = ext.number("closing_balance")
    t = ext.table("transactions")
    if opening is None or closing is None or t is None or not t.rows:
        return []
    net = sum((r.num("amount") or 0.0) for r in t.rows)
    ok = abs(opening + net - closing) <= 0.01
    return [Check(rule="Running balance reconciles", passed=ok,
                  reason=(f"Opening {opening:.2f} + transactions {net:.2f} = closing {closing:.2f}." if ok
                          else f"Opening {opening:.2f} + {net:.2f} = {opening+net:.2f}, but closing says {closing:.2f}."))]


# ---------------------------------------------------------------------------
# Packs
# ---------------------------------------------------------------------------

INVOICE = DomainPack(
    name="invoice",
    label="Invoice",
    description="Vendor invoices — totals, tax, line items, and bank details.",
    icon="ReceiptText",
    detect_hints=["invoice", "bill to", "amount due", "subtotal", "tax", "invoice no"],
    integrity_label="Fraud & Tamper Review",
    fields=[
        FieldSpec("invoice_number", "Invoice Number", "id", required=True),
        FieldSpec("invoice_date", "Invoice Date", "date", required=True),
        FieldSpec("vendor_name", "Vendor", "text", required=True),
        FieldSpec("vendor_bank_account", "Bank Account", "id"),
        FieldSpec("currency", "Currency", "text"),
        FieldSpec("subtotal", "Subtotal", "currency"),
        FieldSpec("tax", "Tax", "currency"),
        FieldSpec("total", "Total", "currency", required=True),
    ],
    tables=[TableSpec("line_items", "Line Items", [
        ColumnSpec("description", "Description"),
        ColumnSpec("quantity", "Qty", "number"),
        ColumnSpec("unit_price", "Unit Price", "number"),
        ColumnSpec("amount", "Amount", "number"),
    ])],
    arithmetic=[
        ArithmeticRule("sum_col_equals_field", "Totals reconcile", table="line_items", column="amount", field="subtotal"),
        ArithmeticRule("fields_sum_equals", "Tax math", add_fields=["subtotal", "tax"], field="total"),
        ArithmeticRule("row_product", "Line-item math", table="line_items", factors=["quantity", "unit_price"], result_col="amount"),
    ],
    date_fields=["invoice_date"],
    identity_fields=["invoice_number", "vendor_name"],
    party_field="vendor_name",
    account_field="vendor_bank_account",
    amount_field="total",
)

RECEIPT = DomainPack(
    name="receipt",
    label="Receipt",
    description="Store and expense receipts — merchant, totals, payment method.",
    icon="ShoppingBag",
    detect_hints=["receipt", "merchant", "cashier", "change due", "thank you", "visa", "mastercard"],
    integrity_label="Duplicate & Tamper Review",
    fields=[
        FieldSpec("merchant", "Merchant", "text", required=True),
        FieldSpec("receipt_date", "Date", "date", required=True),
        FieldSpec("payment_method", "Payment Method", "text"),
        FieldSpec("currency", "Currency", "text"),
        FieldSpec("subtotal", "Subtotal", "currency"),
        FieldSpec("tax", "Tax", "currency"),
        FieldSpec("total", "Total", "currency", required=True),
    ],
    tables=[TableSpec("items", "Items", [
        ColumnSpec("description", "Item"),
        ColumnSpec("amount", "Amount", "number"),
    ])],
    arithmetic=[
        ArithmeticRule("fields_sum_equals", "Tax math", add_fields=["subtotal", "tax"], field="total"),
    ],
    date_fields=["receipt_date"],
    identity_fields=["merchant", "total", "receipt_date"],
    party_field="merchant",
    amount_field="total",
)

RESUME = DomainPack(
    name="resume",
    label="Résumé",
    description="Candidate CVs — matched by meaning against a job description.",
    icon="UserRound",
    detect_hints=["resume", "curriculum vitae", "work experience", "education", "skills", "linkedin"],
    integrity_label="Integrity & Consistency",
    fields=[
        FieldSpec("candidate_name", "Candidate", "text", required=True),
        FieldSpec("email", "Email", "email"),
        FieldSpec("phone", "Phone", "text"),
        FieldSpec("current_title", "Current Title", "text"),
        FieldSpec("years_experience", "Years of Experience", "number"),
        FieldSpec("education", "Education", "text"),
        FieldSpec("skills", "Skills", "text"),
        FieldSpec("summary", "Summary", "text"),
    ],
    tables=[TableSpec("experience", "Experience", [
        ColumnSpec("company", "Company"),
        ColumnSpec("role", "Role"),
        ColumnSpec("start", "Start"),
        ColumnSpec("end", "End"),
    ])],
    identity_fields=["email"],
    party_field="candidate_name",
    similarity=SimilaritySpec(
        second_input_key="job_description",
        second_input_label="Job description",
        label="Résumé ↔ Job description match",
        signature_fields=["current_title", "skills", "summary", "education"],
        signature_tables=["experience"],
    ),
)

PURCHASE_ORDER = DomainPack(
    name="purchase_order",
    label="Purchase Order",
    description="POs — line items, quantities, and totals for three-way match.",
    icon="ClipboardList",
    detect_hints=["purchase order", "p.o.", "po number", "ship to", "vendor"],
    integrity_label="Duplicate & Tamper Review",
    fields=[
        FieldSpec("po_number", "PO Number", "id", required=True),
        FieldSpec("vendor_name", "Vendor", "text", required=True),
        FieldSpec("order_date", "Order Date", "date", required=True),
        FieldSpec("currency", "Currency", "text"),
        FieldSpec("total", "Total", "currency", required=True),
    ],
    tables=[TableSpec("line_items", "Line Items", [
        ColumnSpec("description", "Description"),
        ColumnSpec("quantity", "Qty", "number"),
        ColumnSpec("unit_price", "Unit Price", "number"),
        ColumnSpec("amount", "Amount", "number"),
    ])],
    arithmetic=[
        ArithmeticRule("sum_col_equals_field", "Totals reconcile", table="line_items", column="amount", field="total"),
        ArithmeticRule("row_product", "Line-item math", table="line_items", factors=["quantity", "unit_price"], result_col="amount"),
    ],
    date_fields=["order_date"],
    identity_fields=["po_number"],
    party_field="vendor_name",
    amount_field="total",
)

CONTRACT = DomainPack(
    name="contract",
    label="Contract",
    description="Agreements — parties, term dates, value, and governing law.",
    icon="FileSignature",
    detect_hints=["agreement", "contract", "party", "hereby", "governing law", "term"],
    integrity_label="Consistency & Risk",
    fields=[
        FieldSpec("party_a", "Party A", "text", required=True),
        FieldSpec("party_b", "Party B", "text", required=True),
        FieldSpec("effective_date", "Effective Date", "date"),
        FieldSpec("end_date", "End Date", "date"),
        FieldSpec("value", "Contract Value", "currency"),
        FieldSpec("governing_law", "Governing Law", "text"),
    ],
    date_fields=["effective_date", "end_date"],
    identity_fields=["party_a", "party_b", "effective_date"],
    party_field="party_a",
    amount_field="value",
    extra_checks=[_contract_date_order],
)

ID_DOCUMENT = DomainPack(
    name="id_document",
    label="ID Document",
    description="Passports & licenses — number, expiry, and authenticity signals.",
    icon="IdCard",
    detect_hints=["passport", "driver", "licence", "license", "identity card", "nationality", "date of birth"],
    integrity_label="Authenticity Signals",
    fields=[
        FieldSpec("full_name", "Full Name", "text", required=True),
        FieldSpec("document_number", "Document Number", "id", required=True),
        FieldSpec("date_of_birth", "Date of Birth", "date"),
        FieldSpec("expiry_date", "Expiry Date", "date", required=True),
        FieldSpec("issuing_authority", "Issuing Authority", "text"),
        FieldSpec("nationality", "Nationality", "text"),
    ],
    date_fields=["date_of_birth", "expiry_date"],
    identity_fields=["document_number"],
    party_field="full_name",
    extra_checks=[_id_checks],
)

BANK_STATEMENT = DomainPack(
    name="bank_statement",
    label="Bank Statement",
    description="Statements — transactions with a reconciling running balance.",
    icon="Landmark",
    detect_hints=["statement", "opening balance", "closing balance", "account number", "transactions"],
    integrity_label="Reconciliation & Tamper",
    fields=[
        FieldSpec("account_holder", "Account Holder", "text", required=True),
        FieldSpec("account_number", "Account Number", "id"),
        FieldSpec("statement_period", "Statement Period", "text"),
        FieldSpec("opening_balance", "Opening Balance", "currency"),
        FieldSpec("closing_balance", "Closing Balance", "currency"),
    ],
    tables=[TableSpec("transactions", "Transactions", [
        ColumnSpec("date", "Date", "date"),
        ColumnSpec("description", "Description"),
        ColumnSpec("amount", "Amount", "number"),
        ColumnSpec("balance", "Balance", "number"),
    ])],
    identity_fields=["account_number", "statement_period"],
    party_field="account_holder",
    extra_checks=[_bank_balance],
)

GENERIC = DomainPack(
    name="generic",
    label="Any Document",
    description="Unknown or new document type — extract everything, flag for review.",
    icon="FileScan",
    detect_hints=[],
    integrity_label="Integrity & Risk",
    fields=[
        FieldSpec("document_title", "Document Title", "text"),
        FieldSpec("primary_date", "Date", "date"),
        FieldSpec("primary_party", "Primary Party", "text"),
        FieldSpec("primary_amount", "Primary Amount", "currency"),
    ],
    date_fields=["primary_date"],
    party_field="primary_party",
)

ALL_PACKS = [
    INVOICE, RECEIPT, RESUME, PURCHASE_ORDER, CONTRACT, ID_DOCUMENT, BANK_STATEMENT, GENERIC,
]
