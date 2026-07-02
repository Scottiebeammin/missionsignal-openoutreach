from dataclasses import dataclass

from openoutreach.funding.models import (
    DocumentVaultItem,
    EvidenceLibraryItem,
    Opportunity,
    OpportunityDocumentRequirement,
)


CRITICAL_DOCUMENT_TYPES = {
    DocumentVaultItem.DocumentType.IRS_DETERMINATION_LETTER,
    DocumentVaultItem.DocumentType.W9,
    DocumentVaultItem.DocumentType.ANNUAL_BUDGET,
    DocumentVaultItem.DocumentType.PROGRAM_BUDGET,
    DocumentVaultItem.DocumentType.OUTCOME_REPORT,
}


@dataclass(frozen=True)
class DocumentVaultSummary:
    total_documents: int
    available_documents: int
    missing_documents: int
    needs_update_documents: int
    readiness_score: int
    grouped_by_status: list[tuple[str, list[DocumentVaultItem]]]
    grouped_by_type: list[tuple[str, list[DocumentVaultItem]]]
    missing_critical_documents: list[str]


@dataclass(frozen=True)
class EvidenceLibrarySummary:
    total_evidence_items: int
    outcome_evidence: int
    impact_stories: int
    needs_update_items: int
    missing_items: int
    readiness_score: int
    grouped_by_status: list[tuple[str, list[EvidenceLibraryItem]]]
    grouped_by_type: list[tuple[str, list[EvidenceLibraryItem]]]
    missing_evidence_items: list[str]


@dataclass(frozen=True)
class OpportunityDocumentSummary:
    requirements: list[OpportunityDocumentRequirement]
    required_documents: list[OpportunityDocumentRequirement]
    needed_evidence: list[OpportunityDocumentRequirement]
    available_requirements: int
    missing_requirements: int
    needs_update_requirements: int
    document_readiness_score: int
    evidence_readiness_score: int
    submission_readiness_score: int
    blocked_by_missing_documents: bool


@dataclass(frozen=True)
class DocumentEvidenceHealth:
    document_summary: DocumentVaultSummary
    evidence_summary: EvidenceLibrarySummary
    opportunities_blocked_by_missing_documents: int


def _score(available: int, needs_update: int, missing: int) -> int:
    total = available + needs_update + missing
    if not total:
        return 0
    return round(((available * 100) + (needs_update * 55)) / total)


def _group(items, choices, attr_name):
    groups = []
    for value, label in choices:
        group_items = [item for item in items if getattr(item, attr_name) == value]
        if group_items:
            groups.append((label, group_items))
    return groups


def document_for_title(project, title: str, documents: list[DocumentVaultItem] | None = None) -> DocumentVaultItem | None:
    normalized = title.casefold()
    if documents is None:
        documents = list(DocumentVaultItem.objects.filter(project=project).order_by("title"))
    for document in documents:
        if document.title.casefold() == normalized or document.get_document_type_display().casefold() == normalized:
            return document

    def _first_of(document_type: str) -> DocumentVaultItem | None:
        return next((d for d in documents if d.document_type == document_type), None)

    if "irs" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.IRS_DETERMINATION_LETTER)
    if "w-9" in normalized or "w9" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.W9)
    if "annual budget" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.ANNUAL_BUDGET)
    if "program budget" in normalized or "budget" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.PROGRAM_BUDGET)
    if "outcome" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.OUTCOME_REPORT)
    if "insurance" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.INSURANCE)
    if "policy" in normalized:
        return _first_of(DocumentVaultItem.DocumentType.POLICY_DOCUMENT)
    return None


def _requirement_status_for_document(document: DocumentVaultItem | None) -> str:
    if not document:
        return OpportunityDocumentRequirement.Status.MISSING
    if document.status == DocumentVaultItem.Status.AVAILABLE:
        return OpportunityDocumentRequirement.Status.AVAILABLE
    if document.status == DocumentVaultItem.Status.NEEDS_UPDATE:
        return OpportunityDocumentRequirement.Status.NEEDS_UPDATE
    if document.status == DocumentVaultItem.Status.ARCHIVED:
        return OpportunityDocumentRequirement.Status.NEEDS_UPDATE
    return OpportunityDocumentRequirement.Status.MISSING


def suggested_requirement_definitions(opportunity: Opportunity):
    types = OpportunityDocumentRequirement.RequirementType
    if opportunity.opportunity_type == Opportunity.OpportunityType.GRANT:
        return [
            ("IRS Determination Letter", types.COMPLIANCE_DOCUMENT),
            ("W-9", types.FINANCIAL_DOCUMENT),
            ("Annual Budget", types.FINANCIAL_DOCUMENT),
            ("Program Budget", types.FINANCIAL_DOCUMENT),
            ("Outcome Report", types.PROGRAM_EVIDENCE),
        ]
    if opportunity.opportunity_type == Opportunity.OpportunityType.CONTRACT:
        return [
            ("W-9", types.FINANCIAL_DOCUMENT),
            ("Insurance", types.COMPLIANCE_DOCUMENT),
            ("Program Budget", types.FINANCIAL_DOCUMENT),
            ("Policy Document", types.COMPLIANCE_DOCUMENT),
            ("Prior Performance Evidence", types.PROGRAM_EVIDENCE),
        ]
    if opportunity.opportunity_type == Opportunity.OpportunityType.PARTNERSHIP:
        return [
            ("One-page program overview", types.REQUIRED_DOCUMENT),
            ("Outcome evidence", types.PROGRAM_EVIDENCE),
            ("Partner letter", types.PARTNERSHIP_EVIDENCE),
            ("Program description", types.REQUIRED_DOCUMENT),
        ]
    if opportunity.opportunity_type == Opportunity.OpportunityType.RESOURCE:
        return [
            ("Program description", types.REQUIRED_DOCUMENT),
            ("Community need data", types.SUPPORTING_EVIDENCE),
            ("Organization profile", types.REQUIRED_DOCUMENT),
        ]
    return [
        ("Program description", types.REQUIRED_DOCUMENT),
        ("Program Budget", types.FINANCIAL_DOCUMENT),
        ("Outcome evidence", types.PROGRAM_EVIDENCE),
    ]


def ensure_opportunity_document_requirements(
    project, opportunity: Opportunity, vault_documents: list[DocumentVaultItem] | None = None
) -> list[OpportunityDocumentRequirement]:
    # Read-mostly: this runs during dashboard/readiness GETs for every opportunity,
    # so it must not issue writes when nothing changed (update_or_create here used
    # to mean thousands of queries WITH WRITES on a single page render).
    # .all() (not .select_related on the manager) so a caller's prefetch cache is honored.
    existing = {
        requirement.title: requirement
        for requirement in opportunity.document_requirements.all()
    }
    if vault_documents is None:
        vault_documents = list(DocumentVaultItem.objects.filter(project=project).order_by("title"))
    to_create: list[OpportunityDocumentRequirement] = []
    to_update: list[OpportunityDocumentRequirement] = []
    for title, requirement_type in suggested_requirement_definitions(opportunity):
        linked_document = document_for_title(project, title, vault_documents)
        status = _requirement_status_for_document(linked_document)
        current = existing.get(title)
        if current is None:
            to_create.append(OpportunityDocumentRequirement(
                opportunity=opportunity,
                title=title,
                requirement_type=requirement_type,
                linked_document=linked_document,
                status=status,
                notes="Deterministic requirement suggestion for this opportunity type.",
            ))
        elif (
            current.requirement_type != requirement_type
            or current.linked_document_id != (linked_document.pk if linked_document else None)
            or current.status != status
        ):
            current.requirement_type = requirement_type
            current.linked_document = linked_document
            current.status = status
            to_update.append(current)
    if to_create:
        OpportunityDocumentRequirement.objects.bulk_create(to_create)
    if to_update:
        OpportunityDocumentRequirement.objects.bulk_update(
            to_update, ["requirement_type", "linked_document", "status"]
        )
    if to_create or to_update:
        return list(opportunity.document_requirements.select_related("linked_document").all())
    return list(existing.values())


def build_document_vault_summary(project) -> DocumentVaultSummary:
    documents = list(DocumentVaultItem.objects.filter(project=project).order_by("document_type", "title"))
    available = sum(1 for item in documents if item.status == DocumentVaultItem.Status.AVAILABLE)
    missing = sum(1 for item in documents if item.status == DocumentVaultItem.Status.MISSING)
    needs_update = sum(1 for item in documents if item.status == DocumentVaultItem.Status.NEEDS_UPDATE)
    available_critical = {
        item.document_type
        for item in documents
        if item.status == DocumentVaultItem.Status.AVAILABLE
    }
    missing_critical = [
        label
        for value, label in DocumentVaultItem.DocumentType.choices
        if value in CRITICAL_DOCUMENT_TYPES and value not in available_critical
    ]
    return DocumentVaultSummary(
        total_documents=len(documents),
        available_documents=available,
        missing_documents=missing,
        needs_update_documents=needs_update,
        readiness_score=_score(available, needs_update, missing),
        grouped_by_status=_group(documents, DocumentVaultItem.Status.choices, "status"),
        grouped_by_type=_group(documents, DocumentVaultItem.DocumentType.choices, "document_type"),
        missing_critical_documents=missing_critical,
    )


def build_evidence_library_summary(project) -> EvidenceLibrarySummary:
    evidence_items = list(EvidenceLibraryItem.objects.filter(project=project).order_by("evidence_type", "title"))
    available = sum(1 for item in evidence_items if item.status == EvidenceLibraryItem.Status.AVAILABLE)
    missing = sum(1 for item in evidence_items if item.status == EvidenceLibraryItem.Status.MISSING)
    needs_update = sum(1 for item in evidence_items if item.status == EvidenceLibraryItem.Status.NEEDS_UPDATE)
    missing_evidence = [
        item.get_evidence_type_display()
        for item in evidence_items
        if item.status == EvidenceLibraryItem.Status.MISSING
    ]
    return EvidenceLibrarySummary(
        total_evidence_items=len(evidence_items),
        outcome_evidence=sum(
            1 for item in evidence_items if item.evidence_type == EvidenceLibraryItem.EvidenceType.OUTCOME_METRIC
        ),
        impact_stories=sum(
            1 for item in evidence_items if item.evidence_type == EvidenceLibraryItem.EvidenceType.IMPACT_STORY
        ),
        needs_update_items=needs_update,
        missing_items=missing,
        readiness_score=_score(available, needs_update, missing),
        grouped_by_status=_group(evidence_items, EvidenceLibraryItem.Status.choices, "status"),
        grouped_by_type=_group(evidence_items, EvidenceLibraryItem.EvidenceType.choices, "evidence_type"),
        missing_evidence_items=missing_evidence,
    )


def build_opportunity_document_summary(
    project, opportunity: Opportunity, vault_documents=None
) -> OpportunityDocumentSummary:
    requirements = ensure_opportunity_document_requirements(project, opportunity, vault_documents=vault_documents)
    document_requirements = [
        item
        for item in requirements
        if item.requirement_type in {
            OpportunityDocumentRequirement.RequirementType.REQUIRED_DOCUMENT,
            OpportunityDocumentRequirement.RequirementType.FINANCIAL_DOCUMENT,
            OpportunityDocumentRequirement.RequirementType.COMPLIANCE_DOCUMENT,
        }
    ]
    evidence_requirements = [
        item
        for item in requirements
        if item.requirement_type in {
            OpportunityDocumentRequirement.RequirementType.SUPPORTING_EVIDENCE,
            OpportunityDocumentRequirement.RequirementType.PROGRAM_EVIDENCE,
            OpportunityDocumentRequirement.RequirementType.PARTNERSHIP_EVIDENCE,
        }
    ]
    available = sum(1 for item in requirements if item.status == OpportunityDocumentRequirement.Status.AVAILABLE)
    missing = sum(1 for item in requirements if item.status == OpportunityDocumentRequirement.Status.MISSING)
    needs_update = sum(1 for item in requirements if item.status == OpportunityDocumentRequirement.Status.NEEDS_UPDATE)
    doc_available = sum(1 for item in document_requirements if item.status == OpportunityDocumentRequirement.Status.AVAILABLE)
    doc_missing = sum(1 for item in document_requirements if item.status == OpportunityDocumentRequirement.Status.MISSING)
    doc_update = sum(1 for item in document_requirements if item.status == OpportunityDocumentRequirement.Status.NEEDS_UPDATE)
    ev_available = sum(1 for item in evidence_requirements if item.status == OpportunityDocumentRequirement.Status.AVAILABLE)
    ev_missing = sum(1 for item in evidence_requirements if item.status == OpportunityDocumentRequirement.Status.MISSING)
    ev_update = sum(1 for item in evidence_requirements if item.status == OpportunityDocumentRequirement.Status.NEEDS_UPDATE)
    document_score = _score(doc_available, doc_update, doc_missing)
    evidence_score = _score(ev_available, ev_update, ev_missing)
    submission_score = round((document_score + evidence_score) / 2) if evidence_requirements else document_score
    return OpportunityDocumentSummary(
        requirements=requirements,
        required_documents=document_requirements,
        needed_evidence=evidence_requirements,
        available_requirements=available,
        missing_requirements=missing,
        needs_update_requirements=needs_update,
        document_readiness_score=document_score,
        evidence_readiness_score=evidence_score,
        submission_readiness_score=submission_score,
        blocked_by_missing_documents=missing > 0,
    )


def build_document_evidence_health(project) -> DocumentEvidenceHealth:
    blocked = (
        Opportunity.objects
        .filter(document_requirements__status__in=[
            OpportunityDocumentRequirement.Status.MISSING,
            OpportunityDocumentRequirement.Status.NEEDS_UPDATE,
        ])
        .distinct()
        .count()
    )
    return DocumentEvidenceHealth(
        document_summary=build_document_vault_summary(project),
        evidence_summary=build_evidence_library_summary(project),
        opportunities_blocked_by_missing_documents=blocked,
    )
