import enum

class ProposalStatus(enum.Enum):
    open = 1
    closed_to_new_participants = 2
    finalized = 3
    cancelled = 4