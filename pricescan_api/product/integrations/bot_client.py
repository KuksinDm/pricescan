import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotClient:
    service_token: str
    send_message_url: str
    send_alert_url: str
    timeout: int = 10

    def _headers(self) -> dict:
        return {
            "X-Service-Token": self.service_token,
            "Content-Type": "application/json",
        }

    def send_message(self, user_id: int, message: str) -> bool:
        try:
            request = requests.post(
                self.send_message_url,
                json={"user_id": user_id, "message": message},
                headers=self._headers(),
                timeout=self.timeout,
            )
            request.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return False

    def send_alert(self, alert: dict) -> bool:
        try:
            request = requests.post(
                self.send_alert_url,
                json=alert,
                headers=self._headers(),
                timeout=self.timeout,
            )
            request.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
