from app.domain.models.document import Document


def enrich_document(
    existing: Document,
    incoming_status,
    incoming_title: str | None = None,
    incoming_disc: str | None = None,
):
    """
    Forward-only update for document lifecycle fields.
    """
    # Forward-only status update
    if incoming_status and existing.status != incoming_status:
        existing.status = incoming_status

    # Title enrichment (only if missing)
    if incoming_title and not existing.title:
        existing.title = incoming_title

    # Description enrichment (only if missing)
    if incoming_disc and not existing.discipline:
        existing.discipline = incoming_disc