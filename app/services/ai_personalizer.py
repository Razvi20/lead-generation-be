import logging
import os

from openai import AsyncOpenAI

from app.config import get_settings

try:
    from langsmith import tracing_context
    from langsmith.wrappers import wrap_openai

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

logger = logging.getLogger(__name__)


async def draft_email(
    body_text: str,
    business_name: str,
    sector: str,
    portfolio_url: str,
) -> str:
    """Generate a personalized cold email using GPT-4o."""
    settings = get_settings()

    if settings.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    if settings.LANGSMITH_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    if settings.LANGSMITH_PROJECT:
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_TRACING"] = "true" if settings.LANGSMITH_TRACING else "false"

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    if settings.LANGSMITH_TRACING and LANGSMITH_AVAILABLE:
        client = wrap_openai(client)
    elif settings.LANGSMITH_TRACING and not LANGSMITH_AVAILABLE:
        logger.warning(
            "LangSmith tracing is enabled but 'langsmith' package is not installed. "
            "Install it to capture OpenAI traces."
        )

    system_prompt = (
        f"You are an expert web development consultant. "
        f"Based on the scraped text of this {sector} company's website, "
        f"write a professional cold email (under 150 words) to the owner. "
        f"Pitch a modern, high-conversion website upgrade that will help them get more {sector} clients. "
        f"Reference their specific services found in the text. "
        f"Point them to my portfolio: {portfolio_url}."
    )

    user_message = (
        f"Business name: {business_name}\n\n"
        f"Website text:\n{body_text[:1500]}"
    )

    try:
        if settings.LANGSMITH_TRACING and LANGSMITH_AVAILABLE:
            with tracing_context(enabled=True):
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=300,
                    temperature=0.7,
                )
        else:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=300,
                temperature=0.7,
            )
        return response.choices[0].message.content or ""
    except Exception:
        logger.exception("OpenAI API call failed for business=%s", business_name)
        return ""
