from enum import Enum


class ReviewAction(str, Enum):
    APPROVE = "approve"
    WBS = "wbs"
    RAID = "raid"
    BOTH = "both"
    QUIT = "quit"


REVIEW_MENU = """
  [1] Approve — finalize and save status.json
  [2] WBS feedback — revise work breakdown
  [3] RAID feedback — revise RAID log
  [4] Both — revise WBS and RAID
  [5] Quit — exit without approving
"""


def parse_review_choice(raw: str) -> ReviewAction | None:
    """Accept numbers, single-letter shortcuts, or descriptive words."""
    choice = raw.strip().lower()
    aliases: dict[str, ReviewAction] = {
        "1": ReviewAction.APPROVE,
        "a": ReviewAction.APPROVE,
        "approve": ReviewAction.APPROVE,
        "2": ReviewAction.WBS,
        "w": ReviewAction.WBS,
        "wbs": ReviewAction.WBS,
        "wbs feedback": ReviewAction.WBS,
        "3": ReviewAction.RAID,
        "r": ReviewAction.RAID,
        "raid": ReviewAction.RAID,
        "raid feedback": ReviewAction.RAID,
        "4": ReviewAction.BOTH,
        "b": ReviewAction.BOTH,
        "both": ReviewAction.BOTH,
        "5": ReviewAction.QUIT,
        "q": ReviewAction.QUIT,
        "quit": ReviewAction.QUIT,
        "exit": ReviewAction.QUIT,
    }
    return aliases.get(choice)
