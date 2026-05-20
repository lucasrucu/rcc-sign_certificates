from enum import Enum


class SubsystemStatus(Enum):
    NOT_UPLOADED = "NOT_UPLOADED"
    SIGNED = "SIGNED"
    NOT_SIGNED = "NOT_SIGNED"
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED"