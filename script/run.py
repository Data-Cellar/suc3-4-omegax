import asyncio
import logging
import os
import pprint

import coloredlogs
import httpx
from dotenv import load_dotenv
from edcpy.edc_api import ConnectorController
from edcpy.messaging import HttpPullMessage, with_messaging_app

_COUNTERPARTY_PROTOCOL_URL = "http://edc:11003/api/dsp"
_COUNTERPARTY_CONNECTOR_ID = "my-edc"
_COUNTERPARTY_ASSET = "GET-consumption"

# Load environment variables from .env.example-script file located in the same directory
# as this script. These variables configure the EDC connector connection details like
# host, ports, API keys, etc. This is a convention of the edcpy client library.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_SCRIPT_DIR, ".env.script"))

_logger = logging.getLogger(__name__)


async def pull_handler(message: dict, queue: asyncio.Queue):
    """Put an HTTP Pull message received from the Rabbit broker into a queue."""

    message = HttpPullMessage(**message)

    _logger.info(
        "Putting HTTP Pull request into the queue:\n%s", pprint.pformat(message.dict())
    )

    # Using a queue is not strictly necessary.
    # We just need an asyncio-compatible way to pass
    # the messages from the broker to the main function.
    await queue.put(message)


async def request_get(
    counter_party_protocol_url: str,
    counter_party_connector_id: str,
    asset_query: str,
    controller: ConnectorController,
    queue: asyncio.Queue,
    queue_timeout_seconds: int = 30,
):
    """Demonstration of a GET request to the Mock HTTP API."""

    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=counter_party_protocol_url,
        counter_party_connector_id=counter_party_connector_id,
        asset_query=asset_query,
    )

    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details, is_provider_push=False
    )

    http_pull_msg = await asyncio.wait_for(queue.get(), timeout=queue_timeout_seconds)

    if http_pull_msg.id != transfer_process_id:
        raise RuntimeError(
            "The ID of the Transfer Process does not match the ID of the HTTP Pull message"
        )

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Sending HTTP GET request with arguments:\n%s",
            pprint.pformat(http_pull_msg.request_args),
        )

        resp = await client.request(**http_pull_msg.request_args)
        _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def main(
    counter_party_protocol_url: str,
    counter_party_connector_id: str,
    asset_query: str,
):
    queue: asyncio.Queue[HttpPullMessage] = asyncio.Queue()

    async def pull_handler_partial(message: dict):
        await pull_handler(message=message, queue=queue)

    # Start RabbitMQ broker and configure handler for HTTP pull messages from Provider
    # These messages (EndpointDataReference) are received by the Consumer Backend
    # For details on why we need a consumer backend and message broker, see:
    # https://github.com/fundacionctic/connector-building-blocks/blob/main/docs/faqs.md
    async with with_messaging_app(http_pull_handler=pull_handler_partial):
        controller = ConnectorController()

        await request_get(
            counter_party_protocol_url=counter_party_protocol_url,
            counter_party_connector_id=counter_party_connector_id,
            asset_query=asset_query,
            controller=controller,
            queue=queue,
        )


if __name__ == "__main__":
    coloredlogs.install(level="DEBUG")

    asyncio.run(
        main(
            counter_party_protocol_url=_COUNTERPARTY_PROTOCOL_URL,
            counter_party_connector_id=_COUNTERPARTY_CONNECTOR_ID,
            asset_query=_COUNTERPARTY_ASSET,
        )
    )
