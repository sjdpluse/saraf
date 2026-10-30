"""Execute existing Saraf jobs.py from an ephemeral GitHub Actions runner.

No long-lived Railway process and NO rewritten Meta/FX business behavior.
The exact original async jobs read their original config.py env variables,
and the original Supabase DB remains canonical. Disabled by default.
"""
import argparse
import asyncio
import os


async def main(task: str) -> None:
    from jobs import (
        fetch_and_store_snapshot,
        fetch_and_store_local_market,
        check_and_post_facebook_update,
        check_and_post_instagram_update,
    )
    handlers = {
        "reference": fetch_and_store_snapshot,
        "local": fetch_and_store_local_market,
        "facebook": check_and_post_facebook_update,
        "instagram": check_and_post_instagram_update,
    }
    await handlers[task](None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True,
        choices=("reference", "local", "facebook", "instagram"))
    args = parser.parse_args()
    if os.getenv("SARAF_ORIGINAL_JOBS_ENABLED") != "true":
        raise SystemExit("Original scheduled jobs are DISABLED (fail closed).")
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        raise SystemExit("Original Supabase environment is incomplete.")
    if args.task in ("facebook", "instagram"):
        if not (os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") if args.task == "facebook"
                else os.getenv("INSTAGRAM_USER_ACCESS_TOKEN")):
            raise SystemExit("Original Meta posting token is not configured.")
    asyncio.run(main(args.task))
