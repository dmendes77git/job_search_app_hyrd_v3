"""
Unit tests for user manager JSON serialization resilience.
Verifies that datetime, UUID, Enum, Path, set, and complex objects
do not cause TypeError: Object of type X is not JSON serializable.
"""

from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
import uuid
import streamlit as st
import pytest

from src.utils.user_manager import (
    make_json_serializable,
    save_user_workspace,
    get_user_workspace,
    flush_session_to_user_workspace,
)
from src.schemas import JobPosting, WorkType


class SampleTestEnum(str, Enum):
    VAL_A = "alpha"
    VAL_B = "beta"


def test_make_json_serializable_primitives():
    """Verify standard primitive types pass through unaltered."""
    assert make_json_serializable("test") == "test"
    assert make_json_serializable(123) == 123
    assert make_json_serializable(45.67) == 45.67
    assert make_json_serializable(True) is True
    assert make_json_serializable(None) is None


def test_make_json_serializable_dates_and_times():
    """Verify datetimes and dates are converted to ISO 8601 strings."""
    dt = datetime(2026, 10, 8, 14, 30, 0, tzinfo=timezone.utc)
    d = date(2026, 10, 8)

    assert make_json_serializable(dt) == "2026-10-08T14:30:00+00:00"
    assert make_json_serializable(d) == "2026-10-08"


def test_make_json_serializable_enums_uuids_paths():
    """Verify enums, UUIDs, and Path objects convert to primitives."""
    u = uuid.uuid4()
    p = Path("data/test/path.json")

    assert make_json_serializable(SampleTestEnum.VAL_A) == "alpha"
    assert make_json_serializable(u) == str(u)
    assert make_json_serializable(p) == str(p)


def test_make_json_serializable_nested_structures():
    """Verify sets, lists, tuples, and nested dicts are recursively transformed."""
    data = {
        "dates": [datetime(2026, 1, 1), date(2026, 2, 2)],
        "set_values": {"apple", "banana"},
        "nested": {
            "enum": SampleTestEnum.VAL_B,
            "uuid": uuid.uuid4(),
            "path": Path("some/file"),
        },
    }

    serialized = make_json_serializable(data)
    assert isinstance(serialized["dates"][0], str)
    assert isinstance(serialized["dates"][1], str)
    assert isinstance(serialized["set_values"], list)
    assert serialized["nested"]["enum"] == "beta"
    assert isinstance(serialized["nested"]["uuid"], str)
    assert isinstance(serialized["nested"]["path"], str)


def test_save_and_load_user_workspace_with_datetimes(tmp_path, monkeypatch):
    """Verify save_user_workspace handles datetimes without raising TypeError."""
    # Direct BASE_DATA_DIR to temporary path
    import src.utils.user_manager as um
    monkeypatch.setattr(um, "BASE_DATA_DIR", tmp_path)

    user_id = "usr_test_serialization"
    complex_workspace = {
        "application_pipeline": {
            "job_1": {
                "id": "job_1",
                "title": "Software Engineer",
                "posted_date": datetime.now(timezone.utc),
                "created_at": datetime(2026, 10, 8, 12, 0, 0),
            }
        },
        "saved_jobs": {"job_1", "job_2"},
        "applied_jobs": ["job_3"],
        "discovered_jobs": [
            {
                "id": "job_4",
                "title": "Staff AI Engineer",
                "posted_date": datetime(2026, 10, 7, 9, 30, 0),
            }
        ],
    }

    # Must succeed without throwing TypeError: Object of type datetime is not JSON serializable
    save_user_workspace(user_id, complex_workspace)

    # Verify loaded workspace has preserved strings
    loaded = get_user_workspace(user_id)
    assert "job_1" in loaded["application_pipeline"]
    assert isinstance(loaded["application_pipeline"]["job_1"]["posted_date"], str)
    assert "2026-10-08" in loaded["application_pipeline"]["job_1"]["posted_date"]


def test_flush_session_to_user_workspace_with_datetimes(tmp_path, monkeypatch):
    """Verify flush_session_to_user_workspace safely serializes session state with datetimes."""
    import src.utils.user_manager as um
    monkeypatch.setattr(um, "BASE_DATA_DIR", tmp_path)

    st.session_state["active_user_id"] = "usr_session_test"
    st.session_state["saved_jobs"] = {"job_alpha"}
    st.session_state["applied_jobs"] = set()
    st.session_state["discovered_jobs"] = [
        {
            "id": "job_alpha",
            "title": "DevOps Architect",
            "posted_date": datetime.now(timezone.utc),
        }
    ]
    st.session_state["customized_cvs"] = {
        "job_alpha": "Curated CV Markdown content"
    }

    # Must flush cleanly to disk without TypeError
    flush_session_to_user_workspace()

    loaded = get_user_workspace("usr_session_test")
    assert "job_alpha" in loaded["customized_cvs"]
    assert isinstance(loaded["discovered_jobs"][0]["posted_date"], str)


def test_job_posting_to_dict_posted_date_iso():
    """Verify JobPosting.to_dict converts posted_date datetime to ISO string."""
    now = datetime(2026, 10, 8, 11, 45, 0, tzinfo=timezone.utc)
    job = JobPosting(
        title="Backend Engineer",
        company_name="Cloud Corp",
        posted_date=now,
        work_type=WorkType.REMOTE,
    )
    d = job.to_dict()
    assert isinstance(d["posted_date"], str)
    assert d["posted_date"] == "2026-10-08T11:45:00+00:00"
