import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

CONTEXT_PATH = Path(__file__).parent.parent / "context" / "sun_gallery_agent_context_v3.md"

MODE_PROMPTS = {
    "email": (
        "You are drafting a professional email for Sun Gallery. "
        "Rules:\n"
        "- Always include a Subject line at the top.\n"
        "- Default sender: Joonwha Lee, Manager, Sun Gallery.\n"
        "- Adjust tone based on recipient type: VIP (warm, exclusive), "
        "dealer (professional, partnership-oriented), fair organizer (formal), "
        "media (informative, story-driven), artist (respectful, collaborative).\n"
        "- Be concise. The user consistently prefers shorter emails.\n"
        "- Frame discounts as 'strategic partnership decisions', never simple price cuts.\n"
        "- Never use investment language like 'invest in art'.\n"
        "- End with proper signature block."
    ),
    "whatsapp": (
        "You are composing a WhatsApp reply for Sun Gallery. "
        "Rules:\n"
        "- STRICTLY 3-5 sentences maximum.\n"
        "- Include only essential info (booth number, artist name, dates).\n"
        "- Minimize emoji usage.\n"
        "- Encourage in-person meetings.\n"
        "- Friendly but professional tone."
    ),
    "marketing": (
        "You are creating marketing content for Sun Gallery. "
        "Rules:\n"
        "- Use 'pioneering force' instead of 'longest-running'.\n"
        "- Gallery intro should be 30-40 words in English.\n"
        "- Include technique, medium, and art-historical significance for artist intros.\n"
        "- Balance academic depth with accessible language.\n"
        "- Content types: SNS post, newsletter, artist introduction.\n"
        "- Never expose internal strategy or commercial comparisons between artists."
    ),
    "document": (
        "You are generating a gallery document for Sun Gallery. "
        "Rules:\n"
        "- Document types: Invoice, Condition Report, Certificate of Authenticity, Sale Offer.\n"
        "- Default terms: buyer-arranged collection from gallery storage, "
        "payment before collection, no refunds after collection, "
        "damage claims within 48 hours.\n"
        "- UAE transactions: 5% customs + 5% VAT = 10.25% on CIF value.\n"
        "- Use professional, formal language."
    ),
    "translate": (
        "You are a specialized art translation assistant for Sun Gallery. "
        "Rules:\n"
        "- Translate between Korean (KR), English (EN), and Arabic (AR).\n"
        "- Artist name conventions: 이정지 = Chungji Lee (NOT 이충지/Choongji).\n"
        "- Maintain consistency in art terminology across languages.\n"
        "- Arabic gallery name: معرض صن (Ma'rad San).\n"
        "- Preserve art-specific nuances and cultural context."
    ),
    "fair": (
        "You are a fair preparation assistant for Sun Gallery. "
        "Rules:\n"
        "- Three modes: 'before' (pre-fair checklist and outreach), "
        "'after' (post-fair follow-up and documentation), "
        "'checklist' (comprehensive task list).\n"
        "- Reference the 2026 fair schedule.\n"
        "- Include booth numbers, participating artists, and dates.\n"
        "- Never mention cost concerns or budget limitations externally."
    ),
}

SENDER_INFO = {
    "Joonwha Lee": {
        "name": "Joonwha Lee",
        "title": "Manager",
        "gallery": "Sun Gallery",
        "location": "Seoul, Korea",
        "email": "sungallery1977@gmail.com",
        "phone": "+82 2-734-0458",
    }
}


def load_context(include_internal: bool = False) -> str:
    """Load gallery context, optionally filtering out Section 13 (internal strategy)."""
    if not CONTEXT_PATH.exists():
        return ""
    content = CONTEXT_PATH.read_text(encoding="utf-8")
    if not include_internal:
        content = filter_internal_strategy(content)
    return content


def filter_internal_strategy(content: str) -> str:
    """Remove Section 13 (internal strategy) from context to prevent external exposure."""
    pattern = r"## 13\. 내부 전략.*?(?=\n---|\Z)"
    filtered = re.sub(pattern, "", content, flags=re.DOTALL)
    return filtered


def build_system_prompt(mode: str) -> str:
    """Build the full system prompt with gallery context and mode-specific instructions."""
    context = load_context(include_internal=False)
    mode_prompt = MODE_PROMPTS.get(mode, "")
    return f"{context}\n\n---\n\n{mode_prompt}"


async def generate_response(
    mode: str,
    message: str,
    recipient: str | None = None,
    sender: str = "Joonwha Lee",
    language: str = "en",
) -> str:
    """Call Claude API with gallery context and return the response."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(mode)

    user_message = message
    if recipient:
        user_message = f"Recipient: {recipient}\n\n{message}"
    if language != "en":
        lang_map = {"ko": "Korean", "ar": "Arabic", "en": "English"}
        lang_name = lang_map.get(language, language)
        user_message += f"\n\nPlease respond in {lang_name}."

    sender_info = SENDER_INFO.get(sender, {})
    if sender_info:
        sig = (
            f"\n\nSender signature:\n{sender_info['name']}\n"
            f"{sender_info['title']}, {sender_info['gallery']} | "
            f"{sender_info['location']}\n"
            f"{sender_info['email']} | {sender_info['phone']}"
        )
        user_message += sig

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
