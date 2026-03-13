import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Job, JobStatus, Lead
from app.services import google_places, scraper, ai_personalizer

logger = logging.getLogger(__name__)


async def run_pipeline(
    job_id: uuid.UUID,
    sector: str,
    bounds: dict,
    portfolio_url: str,
    session_factory: async_sessionmaker,
) -> None:
    """Full lead-generation pipeline: Places → Scrape → AI → DB."""
    try:
        # Update status to PROCESSING
        async with session_factory() as session:
            job = await session.get(Job, job_id)
            if not job:
                logger.error("Job %s not found", job_id)
                return
            job.status = JobStatus.PROCESSING
            await session.commit()

        # Step 1: Google Places searchText
        logger.info("[Job %s] Searching Google Places for '%s'", job_id, sector)
        businesses = await google_places.search_text(sector, bounds)
        if not businesses:
            async with session_factory() as session:
                job = await session.get(Job, job_id)
                job.status = JobStatus.COMPLETED
                await session.commit()
            logger.info("[Job %s] No businesses found, completing with 0 leads", job_id)
            return

        # Step 2: Scrape websites
        urls = [b["website"] for b in businesses]
        logger.info("[Job %s] Scraping %d websites", job_id, len(urls))
        scraped_results = await scraper.run_spider(urls)

        # Build a lookup: url -> scraped data
        scraped_map: dict[str, dict] = {}
        for result in scraped_results:
            scraped_map[result.get("url", "")] = result

        # Step 3: AI email drafts + save leads
        leads_to_save: list[Lead] = []

        for biz in businesses:
            scraped = scraped_map.get(biz["website"], {})
            body_text = scraped.get("body_text", "")
            email_found = scraped.get("email")

            # Step 3a: Generate AI email if we have some text
            ai_draft = ""
            if body_text.strip():
                logger.info("[Job %s] Drafting email for '%s'", job_id, biz["business_name"])
                ai_draft = await ai_personalizer.draft_email(
                    body_text=body_text,
                    business_name=biz["business_name"],
                    sector=sector,
                    portfolio_url=portfolio_url,
                )

            leads_to_save.append(
                Lead(
                    job_id=job_id,
                    business_name=biz["business_name"],
                    website=biz["website"],
                    email_found=email_found,
                    review_count=biz.get("review_count", 0),
                    ai_email_draft=ai_draft,
                )
            )

        # Step 4: Persist leads and mark job as completed
        async with session_factory() as session:
            job = await session.get(Job, job_id)
            session.add_all(leads_to_save)
            job.status = JobStatus.COMPLETED
            await session.commit()

        logger.info("[Job %s] Completed with %d leads", job_id, len(leads_to_save))

    except Exception as e:
        logger.exception("[Job %s] Pipeline failed: %s", job_id, e)
        try:
            async with session_factory() as session:
                job = await session.get(Job, job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)[:2000]
                    await session.commit()
        except Exception:
            logger.exception("[Job %s] Failed to update job status to FAILED", job_id)
