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
    industry="finance",
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
    industry="finance",
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
    industry="hr",
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
        skill_match=True,
    ),
)

PURCHASE_ORDER = DomainPack(
    name="purchase_order",
    industry="logistics",
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
    industry="legal",
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
    industry="identity",
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
    industry="banking",
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

# ---------------------------------------------------------------------------
# Extra deterministic helpers for the new packs
# ---------------------------------------------------------------------------

def _date_order(start_key: str, end_key: str, label: str):
    def _check(ext: Extraction) -> List[Check]:
        a = _parse_date(ext.value(start_key))
        b = _parse_date(ext.value(end_key))
        if a and b:
            ok = b >= a
            return [Check(rule=label, passed=ok,
                          reason=(f"{a.isoformat()} → {b.isoformat()}." if ok
                                  else f"End {b.isoformat()} precedes start {a.isoformat()}."))]
        return []
    return _check


# ===========================================================================
# Finance & Accounting
# ===========================================================================

CREDIT_NOTE = DomainPack(
    name="credit_note", label="Credit Note", industry="finance",
    description="Supplier credit/debit notes — amount credited against an invoice.",
    icon="ReceiptText",
    detect_hints=["credit note", "debit note", "credit memo", "against invoice"],
    fields=[
        FieldSpec("note_number", "Credit Note No.", "id", required=True),
        FieldSpec("vendor_name", "Vendor", "text", required=True),
        FieldSpec("note_date", "Date", "date", required=True),
        FieldSpec("original_invoice", "Against Invoice", "id"),
        FieldSpec("reason", "Reason", "text"),
        FieldSpec("total", "Amount Credited", "currency", required=True),
    ],
    date_fields=["note_date"], identity_fields=["note_number", "vendor_name"],
    party_field="vendor_name", amount_field="total",
)

EXPENSE_REPORT = DomainPack(
    name="expense_report", label="Expense Report", industry="finance",
    description="Employee expense claims — line items reconciled to a claimed total.",
    icon="Wallet",
    detect_hints=["expense report", "reimbursement", "claim", "expense claim"],
    fields=[
        FieldSpec("employee", "Employee", "text", required=True),
        FieldSpec("period", "Period", "text"),
        FieldSpec("report_date", "Date", "date"),
        FieldSpec("total", "Total Claimed", "currency", required=True),
    ],
    tables=[TableSpec("expenses", "Expenses", [
        ColumnSpec("description", "Description"), ColumnSpec("category", "Category"),
        ColumnSpec("amount", "Amount", "number"),
    ])],
    arithmetic=[ArithmeticRule("sum_col_equals_field", "Expenses reconcile",
                               table="expenses", column="amount", field="total")],
    date_fields=["report_date"], identity_fields=["employee", "period", "total"],
    party_field="employee", amount_field="total",
)

TAX_FORM = DomainPack(
    name="tax_form", label="Tax Form", industry="finance",
    description="Tax statements (W-2/1099/GST) — IDs and cross-field amounts.",
    icon="FileDigit",
    detect_hints=["w-2", "1099", "tax", "gst", "vat", "taxable", "withholding", "tax year"],
    fields=[
        FieldSpec("form_type", "Form Type", "text"),
        FieldSpec("taxpayer_id", "Taxpayer ID", "id", required=True),
        FieldSpec("taxpayer_name", "Taxpayer", "text", required=True),
        FieldSpec("tax_year", "Tax Year", "text"),
        FieldSpec("gross_income", "Gross Income", "currency"),
        FieldSpec("tax_withheld", "Tax Withheld", "currency"),
    ],
    identity_fields=["taxpayer_id", "tax_year", "form_type"],
    party_field="taxpayer_name", account_field="taxpayer_id", amount_field="gross_income",
)

QUOTE = DomainPack(
    name="quote", label="Quote / Estimate", industry="finance",
    description="Vendor quotes & estimates — priced line items with a validity date.",
    icon="FileText",
    detect_hints=["quotation", "quote", "estimate", "valid until", "proposal"],
    fields=[
        FieldSpec("quote_number", "Quote No.", "id", required=True),
        FieldSpec("vendor_name", "Vendor", "text", required=True),
        FieldSpec("quote_date", "Date", "date"),
        FieldSpec("valid_until", "Valid Until", "date"),
        FieldSpec("total", "Total", "currency", required=True),
    ],
    tables=[TableSpec("line_items", "Line Items", [
        ColumnSpec("description", "Description"), ColumnSpec("quantity", "Qty", "number"),
        ColumnSpec("unit_price", "Unit Price", "number"), ColumnSpec("amount", "Amount", "number"),
    ])],
    arithmetic=[ArithmeticRule("sum_col_equals_field", "Totals reconcile",
                               table="line_items", column="amount", field="total")],
    date_fields=["quote_date", "valid_until"], identity_fields=["quote_number"],
    party_field="vendor_name", amount_field="total",
)

# ===========================================================================
# Banking & Lending
# ===========================================================================

PAY_STUB = DomainPack(
    name="pay_stub", label="Pay Stub", industry="banking",
    description="Salary slips — gross, deductions and net pay reconciled.",
    icon="Banknote",
    detect_hints=["pay stub", "payslip", "salary", "gross pay", "net pay", "earnings", "deductions"],
    fields=[
        FieldSpec("employee", "Employee", "text", required=True),
        FieldSpec("employer", "Employer", "text"),
        FieldSpec("pay_period", "Pay Period", "text"),
        FieldSpec("gross_pay", "Gross Pay", "currency", required=True),
        FieldSpec("deductions", "Deductions", "currency"),
        FieldSpec("net_pay", "Net Pay", "currency", required=True),
    ],
    arithmetic=[ArithmeticRule("fields_sum_equals", "Net pay math",
                               add_fields=["net_pay", "deductions"], field="gross_pay")],
    identity_fields=["employee", "pay_period"], party_field="employee", amount_field="net_pay",
)

LOAN_APPLICATION = DomainPack(
    name="loan_application", label="Loan Application", industry="banking",
    description="Loan/mortgage files — applicant, amount, income and purpose.",
    icon="HandCoins",
    detect_hints=["loan application", "mortgage", "borrower", "loan amount", "annual income"],
    fields=[
        FieldSpec("applicant", "Applicant", "text", required=True),
        FieldSpec("application_date", "Date", "date"),
        FieldSpec("loan_amount", "Loan Amount", "currency", required=True),
        FieldSpec("term_months", "Term (months)", "number"),
        FieldSpec("annual_income", "Annual Income", "currency"),
        FieldSpec("purpose", "Purpose", "text"),
    ],
    date_fields=["application_date"], identity_fields=["applicant", "application_date"],
    party_field="applicant", amount_field="loan_amount",
)

# ===========================================================================
# Insurance & Healthcare
# ===========================================================================

INSURANCE_CLAIM = DomainPack(
    name="insurance_claim", label="Insurance Claim", industry="insurance_health",
    description="Claims — claimant, policy and amount, with duplicate-claim detection.",
    icon="ShieldAlert",
    detect_hints=["claim", "policy number", "insured", "claim amount", "date of loss"],
    fields=[
        FieldSpec("claim_number", "Claim No.", "id", required=True),
        FieldSpec("claimant", "Claimant", "text", required=True),
        FieldSpec("policy_number", "Policy No.", "id"),
        FieldSpec("claim_date", "Claim Date", "date"),
        FieldSpec("claim_amount", "Claim Amount", "currency", required=True),
    ],
    date_fields=["claim_date"], identity_fields=["claim_number", "policy_number"],
    party_field="claimant", amount_field="claim_amount",
)

MEDICAL_BILL = DomainPack(
    name="medical_bill", label="Medical Bill", industry="insurance_health",
    description="Hospital/clinic bills — charges reconciled, duplicate-billing flagged.",
    icon="Stethoscope",
    detect_hints=["patient", "hospital", "clinic", "diagnosis", "medical", "amount due", "invoice"],
    fields=[
        FieldSpec("patient", "Patient", "text", required=True),
        FieldSpec("provider", "Provider", "text"),
        FieldSpec("service_date", "Service Date", "date"),
        FieldSpec("total", "Total", "currency", required=True),
    ],
    tables=[TableSpec("charges", "Charges", [
        ColumnSpec("description", "Service"), ColumnSpec("code", "Code"),
        ColumnSpec("amount", "Amount", "number"),
    ])],
    arithmetic=[ArithmeticRule("sum_col_equals_field", "Charges reconcile",
                               table="charges", column="amount", field="total")],
    date_fields=["service_date"], identity_fields=["patient", "provider", "service_date", "total"],
    party_field="patient", amount_field="total",
)

PRESCRIPTION = DomainPack(
    name="prescription", label="Prescription", industry="insurance_health",
    description="Prescriptions — prescriber, patient and medication list.",
    icon="Pill",
    detect_hints=["prescription", "rx", "dosage", "sig", "refill", "dr.", "mg"],
    fields=[
        FieldSpec("patient", "Patient", "text", required=True),
        FieldSpec("prescriber", "Prescriber", "text", required=True),
        FieldSpec("prescription_date", "Date", "date"),
    ],
    tables=[TableSpec("medications", "Medications", [
        ColumnSpec("drug", "Drug"), ColumnSpec("dosage", "Dosage"), ColumnSpec("quantity", "Qty", "number"),
    ])],
    date_fields=["prescription_date"], identity_fields=["patient", "prescriber", "prescription_date"],
    party_field="patient",
)

# ===========================================================================
# HR & Recruiting
# ===========================================================================

OFFER_LETTER = DomainPack(
    name="offer_letter", label="Offer Letter", industry="hr",
    description="Employment offers — role, compensation and start date.",
    icon="MailCheck",
    detect_hints=["offer", "we are pleased to offer", "position", "annual salary", "start date"],
    fields=[
        FieldSpec("candidate", "Candidate", "text", required=True),
        FieldSpec("employer", "Employer", "text", required=True),
        FieldSpec("role", "Role", "text"),
        FieldSpec("salary", "Salary", "currency"),
        FieldSpec("start_date", "Start Date", "date"),
    ],
    date_fields=["start_date"], identity_fields=["candidate", "employer", "role"],
    party_field="candidate", amount_field="salary",
)

CERTIFICATE = DomainPack(
    name="certificate", label="Certificate", industry="hr",
    description="Degrees & certifications — holder, issuer and credential ID.",
    icon="Award",
    detect_hints=["certificate", "certify", "awarded", "has completed", "credential", "diploma"],
    fields=[
        FieldSpec("holder", "Holder", "text", required=True),
        FieldSpec("issuer", "Issuer", "text", required=True),
        FieldSpec("title", "Title", "text"),
        FieldSpec("issue_date", "Issue Date", "date"),
        FieldSpec("credential_id", "Credential ID", "id"),
    ],
    date_fields=["issue_date"], identity_fields=["credential_id", "holder", "title"],
    party_field="holder",
)

# ===========================================================================
# Identity & KYC
# ===========================================================================

UTILITY_BILL = DomainPack(
    name="utility_bill", label="Utility Bill", industry="identity",
    description="Proof-of-address bills — holder, service address and amount due.",
    icon="Plug",
    detect_hints=["utility", "electricity", "water", "gas bill", "service address", "amount due", "meter"],
    fields=[
        FieldSpec("account_holder", "Account Holder", "text", required=True),
        FieldSpec("provider", "Provider", "text"),
        FieldSpec("service_address", "Service Address", "text", required=True),
        FieldSpec("billing_date", "Billing Date", "date"),
        FieldSpec("amount_due", "Amount Due", "currency"),
    ],
    date_fields=["billing_date"], identity_fields=["account_holder", "billing_date"],
    party_field="account_holder", amount_field="amount_due",
)

# ===========================================================================
# Legal & Real Estate
# ===========================================================================

NDA = DomainPack(
    name="nda", label="NDA", industry="legal",
    description="Non-disclosure agreements — parties and effective term.",
    icon="FileLock2",
    detect_hints=["non-disclosure", "nda", "confidential", "disclosing party", "receiving party"],
    fields=[
        FieldSpec("party_a", "Disclosing Party", "text", required=True),
        FieldSpec("party_b", "Receiving Party", "text", required=True),
        FieldSpec("effective_date", "Effective Date", "date"),
        FieldSpec("expiry_date", "Expiry Date", "date"),
        FieldSpec("governing_law", "Governing Law", "text"),
    ],
    date_fields=["effective_date", "expiry_date"],
    identity_fields=["party_a", "party_b", "effective_date"], party_field="party_a",
    extra_checks=[_date_order("effective_date", "expiry_date", "Term dates ordered")],
)

LEASE_AGREEMENT = DomainPack(
    name="lease_agreement", label="Lease Agreement", industry="legal",
    description="Property leases — landlord, tenant, term and rent.",
    icon="KeyRound",
    detect_hints=["lease", "landlord", "tenant", "premises", "rent", "security deposit"],
    fields=[
        FieldSpec("landlord", "Landlord", "text", required=True),
        FieldSpec("tenant", "Tenant", "text", required=True),
        FieldSpec("property_address", "Property", "text", required=True),
        FieldSpec("start_date", "Start Date", "date"),
        FieldSpec("end_date", "End Date", "date"),
        FieldSpec("monthly_rent", "Monthly Rent", "currency"),
    ],
    date_fields=["start_date", "end_date"],
    identity_fields=["landlord", "tenant", "property_address", "start_date"],
    party_field="landlord", amount_field="monthly_rent",
    extra_checks=[_date_order("start_date", "end_date", "Lease dates ordered")],
)

# ===========================================================================
# Logistics & Trade
# ===========================================================================

BILL_OF_LADING = DomainPack(
    name="bill_of_lading", label="Bill of Lading", industry="logistics",
    description="Shipping BOLs — shipper, consignee, carrier and cargo.",
    icon="Ship",
    detect_hints=["bill of lading", "b/l", "shipper", "consignee", "carrier", "port of loading"],
    fields=[
        FieldSpec("bol_number", "B/L No.", "id", required=True),
        FieldSpec("shipper", "Shipper", "text", required=True),
        FieldSpec("consignee", "Consignee", "text"),
        FieldSpec("carrier", "Carrier", "text"),
        FieldSpec("ship_date", "Date", "date"),
    ],
    date_fields=["ship_date"], identity_fields=["bol_number"], party_field="shipper",
)

PACKING_LIST = DomainPack(
    name="packing_list", label="Packing List", industry="logistics",
    description="Packing lists — items and quantities for goods-received match.",
    icon="PackageOpen",
    detect_hints=["packing list", "packing slip", "carton", "net weight", "quantity", "package"],
    fields=[
        FieldSpec("reference", "Reference", "id", required=True),
        FieldSpec("shipper", "Shipper", "text"),
        FieldSpec("list_date", "Date", "date"),
    ],
    tables=[TableSpec("items", "Items", [
        ColumnSpec("description", "Description"), ColumnSpec("quantity", "Qty", "number"),
    ])],
    date_fields=["list_date"], identity_fields=["reference"], party_field="shipper",
)

DELIVERY_NOTE = DomainPack(
    name="delivery_note", label="Delivery Note", industry="logistics",
    description="Delivery/goods-received notes — supplier and delivered items.",
    icon="Truck",
    detect_hints=["delivery note", "goods received", "grn", "delivered", "received by"],
    fields=[
        FieldSpec("delivery_number", "Delivery No.", "id", required=True),
        FieldSpec("supplier", "Supplier", "text", required=True),
        FieldSpec("delivery_date", "Date", "date"),
    ],
    tables=[TableSpec("items", "Items", [
        ColumnSpec("description", "Description"), ColumnSpec("quantity", "Qty", "number"),
    ])],
    date_fields=["delivery_date"], identity_fields=["delivery_number"], party_field="supplier",
)

# ===========================================================================
# Education & Academic
# ===========================================================================

TRANSCRIPT = DomainPack(
    name="transcript", label="Transcript", industry="academic",
    description="Academic transcripts & mark sheets — courses, grades and GPA.",
    icon="GraduationCap",
    detect_hints=["transcript", "marksheet", "mark sheet", "gpa", "grade", "semester", "credits"],
    fields=[
        FieldSpec("student_name", "Student", "text", required=True),
        FieldSpec("institution", "Institution", "text", required=True),
        FieldSpec("program", "Program", "text"),
        FieldSpec("gpa", "GPA", "number"),
    ],
    tables=[TableSpec("courses", "Courses", [
        ColumnSpec("course", "Course"), ColumnSpec("credits", "Credits", "number"),
        ColumnSpec("grade", "Grade"),
    ])],
    identity_fields=["student_name", "institution", "program"], party_field="student_name",
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
    # Finance & Accounting
    INVOICE, RECEIPT, CREDIT_NOTE, EXPENSE_REPORT, TAX_FORM, QUOTE,
    # Banking & Lending
    BANK_STATEMENT, PAY_STUB, LOAN_APPLICATION,
    # Insurance & Healthcare
    INSURANCE_CLAIM, MEDICAL_BILL, PRESCRIPTION,
    # HR & Recruiting
    RESUME, OFFER_LETTER, CERTIFICATE,
    # Identity & KYC
    ID_DOCUMENT, UTILITY_BILL,
    # Legal & Real Estate
    CONTRACT, NDA, LEASE_AGREEMENT,
    # Logistics & Trade
    PURCHASE_ORDER, BILL_OF_LADING, PACKING_LIST, DELIVERY_NOTE,
    # Education & Academic
    TRANSCRIPT,
    # Universal fallback (keep last)
    GENERIC,
]
