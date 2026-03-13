import logging

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


async def draft_email(
    body_text: str,
    business_name: str,
    sector: str,
    portfolio_url: str,
) -> str:
    """Generate a personalized cold email using GPT-4o."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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
