"""
Test: Startup Reliability
Validates the boot state machine transitions and subsystem readiness tracking.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.startup import AppState, BootState, SubsystemStatus, require_ready


class TestBootStateTransitions:
    def test_initial_state_is_uninitialized(self):
        state = AppState()
        assert state.model_state == BootState.UNINITIALIZED

    def test_not_ready_when_uninitialized(self):
        state = AppState()
        assert state.is_ready is False

    def test_not_ready_when_partial_subsystems(self):
        state = AppState()
        state.model_state = BootState.READY
        state.subsystems = SubsystemStatus()
        state.subsystems.search_engine = True
        state.subsystems.embedding_model = True
        # provider, reranker, rag_pipeline still False
        assert state.is_ready is False

    def test_ready_when_all_subsystems_true(self):
        state = AppState()
        state.model_state = BootState.READY
        state.subsystems = SubsystemStatus()
        state.subsystems.search_engine = True
        state.subsystems.embedding_model = True
        state.subsystems.reranker = True
        state.subsystems.provider = True
        state.subsystems.rag_pipeline = True
        assert state.is_ready is True

    def test_not_ready_in_error_state(self):
        state = AppState()
        state.model_state = BootState.ERROR
        state.subsystems = SubsystemStatus()
        state.subsystems.search_engine = True
        state.subsystems.embedding_model = True
        state.subsystems.reranker = True
        state.subsystems.provider = True
        state.subsystems.rag_pipeline = True
        assert state.is_ready is False


class TestSubsystemStatus:
    def test_failed_subsystems_lists_failures(self):
        ss = SubsystemStatus()
        ss.search_engine = True
        ss.embedding_model = True
        failed = ss.failed_subsystems()
        assert "reranker" in failed
        assert "provider" in failed
        assert "rag_pipeline" in failed
        assert "search_engine" not in failed

    def test_all_ready_when_all_true(self):
        ss = SubsystemStatus()
        ss.search_engine = True
        ss.embedding_model = True
        ss.reranker = True
        ss.provider = True
        ss.rag_pipeline = True
        assert ss.all_ready() is True

    def test_to_dict_contains_all_keys(self):
        ss = SubsystemStatus()
        d = ss.to_dict()
        expected_keys = {"search_engine", "embedding_model", "reranker", "provider", "rag_pipeline"}
        assert set(d.keys()) == expected_keys


class TestReadinessReport:
    def test_report_structure(self):
        state = AppState()
        state.model_state = BootState.LOADING_INDEX
        report = state.readiness_report()
        assert "boot_state" in report
        assert "is_ready" in report
        assert "subsystems" in report
        assert "failed" in report
        assert report["boot_state"] == "LOADING_INDEX"
        assert report["is_ready"] is False


class TestRequireReady:
    def test_raises_503_when_not_ready(self):
        from backend.core.startup import state as global_state
        original = global_state.model_state
        global_state.model_state = BootState.LOADING_MODELS
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_ready()
        assert exc_info.value.status_code == 503
        
        global_state.model_state = original
