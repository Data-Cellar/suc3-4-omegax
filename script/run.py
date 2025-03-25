import asyncio
import logging
import os
import pprint

import coloredlogs
from dotenv import load_dotenv

from edcpy.edc_api import ConnectorController
from edcpy.messaging import HttpPushMessage, with_messaging_app

# URL of the provider's DSP API endpoint
_COUNTERPARTY_PROTOCOL_URL = "http://provider/api/dsp"
# Unique identifier of the provider connector
_COUNTERPARTY_CONNECTOR_ID = "provider"
# Asset ID to request from the provider
_COUNTERPARTY_ASSET = "my-asset"

# Configuration for the consumer backend that receives data from the provider
_CONSUMER_BACKEND_BASE_URL = "http://datacellar-connector-backend:44080"
_CONSUMER_BACKEND_PUSH_PATH = "/push"
_CONSUMER_BACKEND_PUSH_METHOD = "POST"

# Load environment variables from .env.example-script file located in the same directory
# as this script. These variables configure the EDC connector connection details like
# host, ports, API keys, etc. This is a convention of the edcpy client library.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_SCRIPT_DIR, ".env.script"))

_logger = logging.getLogger(__name__)


async def push_handler(message: dict, queue: asyncio.Queue):
    """
    Handler for push messages received from the provider.
    Converts the raw message dict to a HttpPushMessage and puts it in the queue.
    """

    message = HttpPushMessage(**message)

    _logger.info(
        "Putting HTTP Push request into the queue:\n%s", pprint.pformat(message.dict())
    )

    # Using a queue is not strictly necessary.
    # We just need an asyncio-compatible way to pass
    # the messages from the broker to the main function.
    await queue.put(message)


async def run_request(
    counter_party_protocol_url: str,
    counter_party_connector_id: str,
    asset_query: str,
    controller: ConnectorController,
    queue: asyncio.Queue,
    queue_timeout_seconds: int = 60,
):
    """
    Executes the full data request flow:
    1. Negotiates contract terms with the provider
    2. Initiates the data transfer
    3. Waits for and processes the push message containing the data
    """

    # Start contract negotiation with the provider
    transfer_details = await controller.run_negotiation_flow(
        counter_party_protocol_url=counter_party_protocol_url,
        counter_party_connector_id=counter_party_connector_id,
        asset_query=asset_query,
    )

    # sink_base_url, sink_path and sink_method are the details of our local Consumer Backend.
    # Multiple path parameters can be added after the base path to be added to the routing key.
    # This enables us to "group" the push messages depending on the path called by the provider.
    sink_path = f"{_CONSUMER_BACKEND_PUSH_PATH}/specific/routing/key"

    # Initiate the data transfer process
    transfer_process_id = await controller.run_transfer_flow(
        transfer_details=transfer_details,
        is_provider_push=True,
        sink_base_url=_CONSUMER_BACKEND_BASE_URL,
        sink_path=sink_path,
        sink_method=_CONSUMER_BACKEND_PUSH_METHOD,
    )

    _logger.info("Transfer process ID: %s", transfer_process_id)

    # Wait for the push message containing the requested data
    http_push_msg = await asyncio.wait_for(queue.get(), timeout=queue_timeout_seconds)

    _logger.info("Received response:\n%s", pprint.pformat(http_push_msg.body))


async def main(
    counter_party_protocol_url: str,
    counter_party_connector_id: str,
    asset_query: str,
):
    """
    Main entry point for the data request script.
    Sets up message handling and executes the request flow.
    """

    queue: asyncio.Queue[HttpPushMessage] = asyncio.Queue()

    async def push_handler_partial(message: dict):
        await push_handler(message=message, queue=queue)

    # Start RabbitMQ broker and configure handler for messages from Provider
    async with with_messaging_app(http_push_handler=push_handler_partial):
        controller = ConnectorController()

        await run_request(
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
