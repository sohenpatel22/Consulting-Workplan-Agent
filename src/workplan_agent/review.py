from enum import Enum


class ReviewAction(str, Enum):
    APPROVE = "approve"
    WBS = "wbs"
    RAID = "raid"
    STAKEHOLDER = "stakeholder"
    STATUS = "status"
    BOTH = "both"
    ALL = "all"
    QUIT = "quit"


REVIEW_MENU = """
  [1] Approve — finalize and save status.json
  [2] WBS feedback — revise work breakdown
  [3] RAID feedback — revise RAID log
  [4] Stakeholder feedback — revise stakeholder map
  [5] Status report feedback — revise weekly status report
  [6] Both — revise WBS and RAID
  [7] All — revise WBS, RAID, Stakeholder, and Status
  [8] Quit — exit without approving
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
        "4": ReviewAction.STAKEHOLDER,
        "s": ReviewAction.STAKEHOLDER,
        "stakeholder": ReviewAction.STAKEHOLDER,
        "stakeholder feedback": ReviewAction.STAKEHOLDER,
        "5": ReviewAction.STATUS,
        "status": ReviewAction.STATUS,
        "status feedback": ReviewAction.STATUS,
        "status report": ReviewAction.STATUS,
        "6": ReviewAction.BOTH,
        "b": ReviewAction.BOTH,
        "both": ReviewAction.BOTH,
        "7": ReviewAction.ALL,
        "all": ReviewAction.ALL,
        "8": ReviewAction.QUIT,
        "q": ReviewAction.QUIT,
        "quit": ReviewAction.QUIT,
        "exit": ReviewAction.QUIT,
    }
    return aliases.get(choice)
