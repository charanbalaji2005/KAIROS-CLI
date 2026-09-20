"""Tests for repository and framework detector."""

from forge.repository.detector import RepositoryDetector


def test_repository_detector_on_workspace():
    info = RepositoryDetector.detect(".")
    assert "Python" in info.languages
    assert "pip" in info.package_managers
