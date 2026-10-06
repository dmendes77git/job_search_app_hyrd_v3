"""Modular dialog components for Hyrd application.

Contains:
- show_cv_dialog (cv_dialog)
- show_cover_letter_dialog (cover_letter_dialog)
- show_interview_prep_dialog (interview_dialog)
- show_outreach_dialog (outreach_dialog)
- show_company_dossier_dialog (company_dialog)
"""

from .cv_dialog import show_cv_dialog
from .cover_letter_dialog import show_cover_letter_dialog
from .interview_dialog import show_interview_prep_dialog
from .outreach_dialog import show_outreach_dialog
from .company_dialog import show_company_dossier_dialog

__all__ = [
    "show_cv_dialog",
    "show_cover_letter_dialog",
    "show_interview_prep_dialog",
    "show_outreach_dialog",
    "show_company_dossier_dialog",
]
