"""
Shared Dialogs for Tailored CV, Cover Letter, Interview Prep, Outreach, and Company Dossier.
Facade module maintaining 100% backwards compatibility with all existing imports.
Modular components are located in src.components.dialogs.
"""

from src.components.dialogs import (
    show_cv_dialog,
    show_cover_letter_dialog,
    show_interview_prep_dialog,
    show_outreach_dialog,
    show_company_dossier_dialog,
)

__all__ = [
    "show_cv_dialog",
    "show_cover_letter_dialog",
    "show_interview_prep_dialog",
    "show_outreach_dialog",
    "show_company_dossier_dialog",
]
