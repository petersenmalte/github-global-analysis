from __future__ import annotations

from dataclasses import replace

from github_global_analysis.attribution import (
    DECLARED_AI,
    DECLARED_HUMAN,
    INDETERMINATE,
    classify_commit,
)


def test_explicit_ai_declaration_is_single_primary_category_with_multiple_tools(rules) -> None:
    result = classify_commit(
        "Implement feature\n\nAI-Assisted: yes\nAI-Tools: GitHub Copilot, Claude",
        rules=rules,
    )

    assert result.declared_attribution == DECLARED_AI
    assert result.tool_labels == ("GitHub Copilot", "Claude")
    assert result.is_bot is False


def test_human_declaration_requires_exact_trailer_and_missing_marker_is_indeterminate(rules) -> None:
    prose = classify_commit("The author said this was Human-Only: yes in prose.", rules=rules)
    explicit = classify_commit("Implement feature\n\nHuman-Only: yes", rules=rules)

    assert prose.declared_attribution == INDETERMINATE
    assert explicit.declared_attribution == DECLARED_HUMAN


def test_conflicting_declarations_and_unknown_tools_are_not_human_evidence(rules) -> None:
    conflict = classify_commit(
        "Change\n\nAI-Assisted: yes\nHuman-Only: yes", rules=rules
    )
    unknown_tool = classify_commit(
        "Change\n\nAI-Assisted: yes\nAI-Tools: Unconfigured Tool", rules=rules
    )

    assert conflict.declared_attribution == INDETERMINATE
    assert unknown_tool.declared_attribution == DECLARED_AI
    assert unknown_tool.tool_labels == ()


def test_conflicting_or_unsupported_primary_trailer_values_are_indeterminate(rules) -> None:
    contradictory_ai = classify_commit(
        "Change\n\nAI-Assisted: yes\nAI-Assisted: no", rules=rules
    )
    contradictory_human = classify_commit(
        "Change\n\nHuman-Only: yes\nHuman-Only: no", rules=rules
    )
    unsupported_ai = classify_commit("Change\n\nAI-Assisted: no", rules=rules)

    for result in (contradictory_ai, contradictory_human, unsupported_ai):
        assert result.declared_attribution == INDETERMINATE
        assert result.evidence == "conflicting-or-invalid-explicit-declarations"


def test_shared_declared_attribution_key_accepts_each_configured_primary_value(rules) -> None:
    declared_ai = classify_commit(
        "Change\n\nDeclared-Attribution: ai-assisted", rules=rules
    )
    declared_human = classify_commit(
        "Change\n\nDeclared-Attribution: human-only", rules=rules
    )

    assert declared_ai.declared_attribution == DECLARED_AI
    assert declared_human.declared_attribution == DECLARED_HUMAN


def test_bot_identity_is_a_separate_dimension_not_ai_attribution(rules) -> None:
    result = classify_commit(
        "Automated update\n\nAI-Assisted: yes\nAI-Tools: GitHub Copilot",
        author_name="release[bot]",
        author_email="41898282+release[bot]@users.noreply.github.com",
        rules=rules,
    )

    assert result.is_bot is True
    assert result.declared_attribution == INDETERMINATE
    assert result.tool_labels == ()


def test_only_configured_exact_coauthor_declaration_is_accepted(rules) -> None:
    configured = replace(
        rules,
        exact_ai_coauthors=(("Configured Assistant", "assistant@example.test"),),
    )

    accepted = classify_commit(
        "Change\n\nCo-authored-by: Configured Assistant <assistant@example.test>",
        rules=configured,
    )
    arbitrary = classify_commit(
        "Change\n\nCo-authored-by: Someone Else <other@example.test>",
        rules=configured,
    )

    assert accepted.declared_attribution == DECLARED_AI
    assert arbitrary.declared_attribution == INDETERMINATE
