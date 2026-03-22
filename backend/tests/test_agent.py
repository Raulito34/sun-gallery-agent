import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import load_context, filter_internal_strategy, build_system_prompt, MODE_PROMPTS


class TestContextLoading:
    def test_load_context_returns_string(self):
        context = load_context()
        assert isinstance(context, str)
        assert len(context) > 0

    def test_load_context_contains_gallery_info(self):
        context = load_context()
        assert "선화랑" in context or "Sun Gallery" in context

    def test_load_context_without_internal_strategy(self):
        context = load_context(include_internal=False)
        # Section 13 heading should be removed
        assert "## 13. 내부 전략" not in context
        # Section 13 specific content should be removed
        assert "투트랙 비즈니스 모델" not in context
        assert "Sun Art Center" not in context or "브랜드 이원화" not in context

    def test_load_context_with_internal_strategy(self):
        context = load_context(include_internal=True)
        assert "내부 전략" in context


class TestFilterInternalStrategy:
    def test_removes_section_13(self):
        sample = (
            "## 12. Some section\nContent here\n\n---\n\n"
            "## 13. 내부 전략 (⚠️ 대외 커뮤니케이션에 절대 노출 금지)\n"
            "Secret stuff here\nMore secrets\n\n---\n\n"
            "## 14. Next section\nPublic content"
        )
        result = filter_internal_strategy(sample)
        assert "내부 전략" not in result
        assert "Secret stuff" not in result
        assert "## 12. Some section" in result

    def test_preserves_other_sections(self):
        sample = (
            "## 1. Gallery Info\nSun Gallery\n\n---\n\n"
            "## 13. 내부 전략\nInternal only\n\n---\n\n"
            "## AI 에이전트 행동 규칙\nRules here"
        )
        result = filter_internal_strategy(sample)
        assert "Gallery Info" in result
        assert "Sun Gallery" in result


class TestBuildSystemPrompt:
    def test_includes_mode_prompt(self):
        prompt = build_system_prompt("email")
        assert "Subject line" in prompt

    def test_includes_context(self):
        prompt = build_system_prompt("email")
        assert "Sun Gallery" in prompt

    def test_all_modes_have_prompts(self):
        for mode in ["email", "whatsapp", "marketing", "document", "translate", "fair"]:
            assert mode in MODE_PROMPTS

    def test_unknown_mode_returns_context_only(self):
        prompt = build_system_prompt("unknown_mode")
        assert "Sun Gallery" in prompt


class TestGenerateResponse:
    @patch("agent.anthropic.Anthropic")
    def test_generate_response_calls_api(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test email draft")]
        mock_client.messages.create.return_value = mock_response

        import asyncio
        from agent import generate_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = asyncio.run(
                generate_response(mode="email", message="Write a follow-up email")
            )

        assert result == "Test email draft"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert "Subject line" in call_kwargs["system"]

    @patch("agent.anthropic.Anthropic")
    def test_generate_response_no_api_key(self, mock_anthropic_class):
        import asyncio
        from agent import generate_response

        with patch.dict("os.environ", {}, clear=True):
            # Remove ANTHROPIC_API_KEY if it exists
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                asyncio.run(
                    generate_response(mode="email", message="Test")
                )
