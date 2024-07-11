import logging
import os
from datetime import datetime, timezone, timedelta

import aiohttp
import azure.functions as func
from connections.sentinel import SentinelConnector
from connections.zerofox import ZeroFoxClient


async def main(mytimer: func.TimerRequest) -> None:
    now = datetime.now(timezone.utc)
    utc_timestamp = (
        now.isoformat()
    )

    if mytimer.past_due:
        logging.info("The timer is past due!")

    customer_id = os.environ.get("WorkspaceID")
    shared_key = os.environ.get("WorkspaceKey")

    query_from = max(
        mytimer.schedule_status["Last"], (now - timedelta(days=1)).isoformat())
    logging.info(f"Querying ZeroFox since {query_from}")

    zerofox = get_zf_client()

    log_type = "ZeroFox_CTI_national_ids"

    async with aiohttp.ClientSession() as session:
        sentinel = SentinelConnector(
            session=session,
            customer_id=customer_id,
            shared_key=shared_key,
            log_type=log_type,
        )
        async with sentinel:
            batches = get_cti_national_ids(
                zerofox, created_after=query_from
            )
            for batch in batches:
                await sentinel.send(batch)
    if sentinel.failed_sent_events_number:
        logging.error(
            f"Failed to send {sentinel.failed_sent_events_number} events"
        )
    logging.info(f"Connector {log_type} ran at {utc_timestamp}, \
                  sending {sentinel.successfull_sent_events_number} events to Sentinel.")


def get_zf_client():
    user = os.environ.get("ZeroFoxUsername")
    token = os.environ.get("ZeroFoxToken")
    return ZeroFoxClient(user, token)


def get_cti_national_ids(
    client: ZeroFoxClient, created_after: str
):
    url_suffix = "national-ids/"
    params = dict(created_after=created_after)
    return client.cti_request(
        "GET",
        url_suffix,
        params=params,
    )
