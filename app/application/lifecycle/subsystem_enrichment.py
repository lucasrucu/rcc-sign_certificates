from app.domain.models.subsystem import Subsystem


def enrich_subsystem(
    existing: Subsystem,
    incoming_status=None,
):
    if incoming_status and existing.status != incoming_status:
        existing.status = incoming_status