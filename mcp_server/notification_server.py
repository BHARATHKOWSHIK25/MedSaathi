"""
notification_server.py
-------------------------
An MCP (Model Context Protocol) server that exposes medication reminder
delivery as a callable tool: `send_reminder`.

Why an MCP server (course concept): wrapping notification delivery as an
MCP tool decouples the orchestrator agent from the delivery mechanism.
Any MCP-compatible agent/client (this pipeline, a future ADK agent, or a
completely different orchestrator) can call `send_reminder` without
knowing whether it's backed by Twilio, a different SMS gateway, or a
simulated log line - the tool contract stays the same.

Run standalone with:  python mcp_server/notification_server.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from agents.security import mask_phone  # noqa: E402

mcp = FastMCP("medsaathi-notifications")


def _send_via_twilio(phone: str, message: str, channel: str) -> dict:
    from twilio.rest import Client

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    if channel == "whatsapp":
        from_number = os.environ["TWILIO_WHATSAPP_FROM"]
        to_number = f"whatsapp:{phone}"
    else:
        from_number = os.environ["TWILIO_SMS_FROM"]
        to_number = phone

    msg = client.messages.create(body=message, from_=from_number, to=to_number)
    return {"status": "sent", "provider_message_id": msg.sid}


@mcp.tool()
def send_reminder(phone: str, message: str, channel: str = "whatsapp") -> dict:
    """Send a medication reminder to a patient via WhatsApp or SMS.

    Args:
        phone: Patient's phone number in E.164 format (e.g. +919876543210).
        message: The localized reminder text to send.
        channel: "whatsapp" or "sms".

    Returns:
        A dict with delivery status. Falls back to a simulated send (no
        real message dispatched) if Twilio credentials are not configured,
        so this tool is always safe to call in a demo environment.
    """
    have_credentials = all(
        os.environ.get(k)
        for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN")
    )

    if have_credentials:
        try:
            result = _send_via_twilio(phone, message, channel)
            result["masked_phone"] = mask_phone(phone)
            return result
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc), "masked_phone": mask_phone(phone)}

    # Simulated send - safe default, no credentials required.
    return {
        "status": "simulated",
        "channel": channel,
        "masked_phone": mask_phone(phone),
        "message_preview": message,
        "note": "Twilio credentials not configured - this is a simulated delivery for demo purposes.",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
