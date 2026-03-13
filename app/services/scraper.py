import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SCRAPER_DIR = Path(__file__).resolve().parent.parent.parent / "scraper"


async def run_spider(urls: list[str]) -> list[dict]:
    """Run the Scrapy website_spider in a subprocess and return parsed results."""
    if not urls:
        return []

    # Write URLs to a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir=tempfile.gettempdir()
    ) as urls_fp:
        json.dump(urls, urls_fp)
        urls_path = urls_fp.name

    # Output file for scraped data
    output_fd, output_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(output_fd)

    try:
        proc = await asyncio.create_subprocess_exec(
            "scrapy",
            "crawl",
            "website_spider",
            "-a",
            f"urls_file={urls_path}",
            "-o",
            f"{output_path}:jsonlines",
            "--nolog",
            cwd=str(SCRAPER_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            logger.error("Scrapy spider failed (rc=%d): %s", proc.returncode, stderr.decode()[:500])

        # Parse output
        results: list[dict] = []
        if os.path.exists(output_path):
            with open(output_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))

        logger.info("Spider returned %d results for %d URLs", len(results), len(urls))
        return results

    except asyncio.TimeoutError:
        logger.error("Scrapy spider timed out after 120s")
        return []
    finally:
        for path in (urls_path, output_path):
            try:
                os.unlink(path)
            except OSError:
                pass
