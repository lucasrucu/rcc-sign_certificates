from enum import Enum


class DocumentStatus(Enum):
    NEW = "NEW"
    DOWNLOADED = "DOWNLOADED"
    UPLOADED_METADATA = "UPLOADED_METADATA"
    UPLOADED_FILE = "UPLOADED_FILE"
    FAILED = "FAILED"


class DocumentType(Enum):
    HOP = "HOP"
    SDD = "SDD"
    

class DocumentDiscipline(Enum):
    MECHANICAL = "Mechanical"
    ELECTRICAL = "Electrical"
    TELECOMMUNICATIONS = "Telecommunication"
    INSTRUMENTS = "Instrument"
    PIPING = "Piping"
    NO_DISC = "No Discipline"
    
    
    
    