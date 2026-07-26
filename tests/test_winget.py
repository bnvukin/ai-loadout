"""Tests for winget outcome interpretation."""

from ai_loadout.actions import winget


def test_winget_upgrade_not_installed_detects_missing_package():
    output = "No installed package found matching input criteria."
    assert winget.winget_upgrade_not_installed(output) is True


def test_winget_already_satisfied_from_output_text():
    output = (
        "Found an existing package already installed. Trying to upgrade the installed package...\n"
        "No available upgrade found."
    )
    assert winget.winget_already_satisfied(2316632107, output) is True


def test_winget_already_satisfied_from_known_exit_code():
    assert winget.winget_already_satisfied(-1978335189, "") is True


def test_winget_failure_is_not_already_satisfied():
    assert winget.winget_already_satisfied(1, "Unexpected error occurred.") is False
