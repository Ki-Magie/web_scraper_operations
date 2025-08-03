import logging
import requests

# Logging wird im Docker main (app.py) definiert
logger = logging.getLogger(__name__)


class RequestClient:

    def __init__(self):
        logger.info(f"RequestClient gestartet")
        self._session = requests.Session()
        self._response = None

    def request_post(self, url, headers, payload):
        logger.info(f"request_post")
        self._response = self._session.post(url, data=payload, headers=headers)
        return self._handle_response()

    def request_get(self, url: str):
        logger.info(f"request_get")
        self._response = self._session.get(url)
        return self._handle_response()

    def get_response(self):
        logger.info(f"get_response")
        return self._response

    def _handle_response(self):
        status = self._response.status_code

        if 200 <= status < 300:
            # Gültige Antwort
            logger.info(f"Erfolg ({status})")
            return True

        elif status in (301, 302):
            # Warnung bei weiterleitung
            location = self._response.headers.get("Location", "Unbekannt")
            logger.warning(f"Weiterleitung ({status}) nach {location}")

        elif status == 400:
            logger.error("Fehlerhafte Anfrage (400): Prüfe deine Daten.")
        elif status == 401:
            logger.error("Nicht autorisiert (401): Login oder Token fehlt.")
        elif status == 403:
            logger.error("Zugriff verweigert (403): Du hast keine Rechte.")
        elif status == 404:
            logger.error("Nicht gefunden (404): URL prüfen.")
        elif status == 429:
            logger.error("Zu viele Anfragen (429): Rate Limit erreicht.")
        elif 500 <= status < 600:
            logger.error(f"Serverfehler ({status}): Problem auf der Serverseite.")
        else:
            logger.warning(f"Unerwarteter Statuscode ({status})")

        return False  # Bei allen Fehlern
