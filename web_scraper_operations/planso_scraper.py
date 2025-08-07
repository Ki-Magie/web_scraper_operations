import os
import logging
import time
from types import SimpleNamespace
import yaml

from .selenium_client import SeleniumClient

# Logging-Konfiguration (wird extern in app.py gesetzt)
logger = logging.getLogger(__name__)


class PlanSoMain:
    """
    Hauptklasse zur Automatisierung der Interaktion mit der PlanSo-Webanwendung via Selenium.
    Die Konfiguration wird aus einer YAML-Datei geladen und in ein Namespace-Objekt umgewandelt.

    Sicherheitshinweis: Keine Zugangsdaten im Code speichern!
    """

    def __init__(
        self,
        username: str,
        password: str,
        table: str,
        table_name: str,
        config: str = None,
        client: str = "jvg",
    ):
        logger.info(
            "Initialisiere PlanSoMain mit Table-ID: %s und Client: %s", table, client
        )
        if config is None:
            config = self._get_config_path()

        self._load_cofig(config, client)
        self._config = self._replace_in_dict(self._config, "TABLE_ID", table)
        self._config = self._replace_in_dict(self._config, "TABLE_NAME", table_name)
        self._config = self._dict_to_namespace(self._config)

        self._selenium_client = SeleniumClient(headless=True)

        # Login-Daten setzen (aus Sicherheitsgründen nicht loggen!)
        self._config.login_payload.system_login_username = username
        self._config.login_payload.system_login_password = password

    def planso_upload_flow(
        self, field_name: str, search_field_name: str, search_string: str, path: str
    ):
        """
        Vollständiger Ablauf für den Datei-Upload: Login, Navigation, Dateiupload, Logout.
        """
        logger.info("Starte Upload-Flow für Datei: %s", path)

        self._selenium_client.open_url(url=self._config.base_url)
        self.login()
        self.open_navigation()
        self.open_table()
        time.sleep(0.5)

        logger.debug("Suche Zielzeile für den Upload...")
        row_info = self.find_element(search_field_name, search_string)

        if row_info is None:
            return {"message": f"no {search_string} in {search_field_name}"}

        logger.debug("Starte Datei-Upload...")
        success = self.upload_file(path, row_info, field_name)
        logger.debug("return of upload_file '%s%'", success)
        self._selenium_client.wait_for_invisibility(
            by=self._config.selenium.wait_for_upload.locator_strategie,
            selector=self._config.selenium.wait_for_upload.selector,
        )

        logger.debug("Schließe Upload-Dialog...")

        self._selenium_client.click(
            by=self._config.selenium.upload_dialog_close.locator_strategie,
            selector=self._config.selenium.upload_dialog_close.selector,
        )
        time.sleep(0.5)
        self.logout()

        logger.info("Upload-Flow abgeschlossen.")
        if success:
            return {"message": f"uploaded"}
        else:
            return {"message": f"not uploaded"}

    def _load_cofig(self, config: str, client: str):
        logger.debug("Lade Konfigurationsdatei: %s", config)
        with open(config, "r") as f:
            self._config = yaml.safe_load(f)[client]

    def login(self):
        try:
            logger.info("Beginne Login-Prozess...")

            self._selenium_client.type_text(
                self._config.selenium.login_username_field.locator_strategie,
                self._config.selenium.login_username_field.selector,
                self._config.login_payload.system_login_username,
            )
            self._selenium_client.type_text(
                self._config.selenium.login_password_field.locator_strategie,
                self._config.selenium.login_password_field.selector,
                self._config.login_payload.system_login_password,
            )
            self._selenium_client.click(
                self._config.selenium.login_submit_button.locator_strategie,
                self._config.selenium.login_submit_button.selector,
            )

            logger.debug("Warte auf Navigationselement (Login-Bestätigung)...")
            self._selenium_client.wait_for_element(
                self._config.selenium.navigation.locator_strategie,
                self._config.selenium.navigation.selector,
            )

            self._selenium_client.wait_for_invisibility(
                self._config.selenium.preload_video.locator_strategie,
                self._config.selenium.preload_video.selector,
            )

            logger.info("Login erfolgreich.")
            return True

        except Exception as e:
            logger.error("Login fehlgeschlagen: %s", str(e))
            return False

    def logout(self):
        logger.info("Führe Logout durch...")
        self._selenium_client.open_url(url=self._config.logout_url)

    def upload_file(self, path, row_info, target_field="Dokumente"):
        logger.info("Starte Datei-Upload für Ziel-Feld: %s", target_field)
        try:
            self.set_page(row_info["page"])
            rows = self._selenium_client.find_elements(
                by=self._config.selenium.rows_of_table.locator_strategie,
                selector=self._config.selenium.rows_of_table.selector,
            )

            target_field_idx = -1
            for idx, row in enumerate(rows):
                if idx == 1 and target_field_idx == -1:
                    tds = self._selenium_client.find_elements(
                        by=self._config.selenium.field_count.locator_strategie,
                        selector=self._config.selenium.field_count.selector,
                        element=row,
                    )
                    for i, td in enumerate(tds):
                        td_id = td.get_attribute("aria-describedby")
                        if td_id == getattr(self._config.table_fields, target_field):
                            target_field_idx = i + 1
                            logger.debug(
                                "Feld '%s' hat Index %d", target_field, target_field_idx
                            )

                if row_info["plate"] in row.text:
                    logger.debug("Klicke Upload-Zelle...")
                    upload_cell = row.find_element(
                        self._config.selenium.upload_cell_prepare.locator_strategie,
                        self._config.selenium.upload_cell_prepare.selector
                        + f"[{target_field_idx}]",
                    )
                    upload_cell.click()
                    time.sleep(0.5)
                    break

            rows = self._selenium_client.find_elements(
                by=self._config.selenium.rows_of_table.locator_strategie,
                selector=self._config.selenium.rows_of_table.selector,
            )
            for row in rows:
                if row_info["plate"] in row.text:
                    self._selenium_client.upload_file(
                        element=row,
                        by=self._config.selenium.upload_cell.locator_strategie,
                        selector=self._config.selenium.upload_cell.selector,
                        path=path,
                    )
                    self._selenium_client.wait_until_not(
                        by=self._config.selenium.status_upload.locator_strategie,
                        selector=self._config.selenium.status_upload.selector,
                    )
                    logger.info("Datei erfolgreich hochgeladen.")
                    return True
        except Exception as e:
            logger.error("Upload fehlgeschlagen: %s", str(e))
        return False

    def find_element(self, field_name: str, search_string: str):
        logger.info(
            "Suche Element mit Feld '%s' und Suchbegriff '%s'",
            field_name,
            search_string,
        )
        self._config.find_element.selector = self._config.find_element.selector.replace(
            "FIELD_STRING", field_name
        )
        nr_pages = self.get_nr_pages()
        field_idx = -1

        for page in range(1, nr_pages + 1):
            self.set_page(page)
            rows = self._selenium_client.find_elements(
                by=self._config.selenium.rows_of_table.locator_strategie,
                selector=self._config.selenium.rows_of_table.selector,
            )
            for idx, row in enumerate(rows):
                if idx == 1 and field_idx == -1:
                    tds = self._selenium_client.find_elements(
                        by=self._config.selenium.field_count.locator_strategie,
                        selector=self._config.selenium.field_count.selector,
                        element=row,
                    )
                    for i, td in enumerate(tds):
                        td_id = td.get_attribute("aria-describedby")
                        if td_id == getattr(self._config.table_fields, field_name):
                            field_idx = i

                if search_string in row.text:
                    logger.debug(
                        "'%s' wurde auf seite '%s' in Zeilenindex '%s' gefunden.",
                        search_string,
                        page,
                        idx,
                    )
                    numberplate = self._selenium_client.find_element(
                        by=self._config.find_element.locator_strategie,
                        selector=self._config.find_element.selector,
                        element=row,
                    ).text
                    id_nr = self._selenium_client.find_element(
                        by=self._config.find_element.locator_strategie,
                        selector=self._config.find_element.selector_id,
                        element=row,
                    ).text
                    logger.info(
                        "Element gefunden: Kennzeichen=%s, ID=%s", numberplate, id_nr
                    )
                    return {
                        "Zeile": idx,
                        "ID": id_nr,
                        "plate": numberplate,
                        "field_idx": field_idx,
                        "page_size": self.get_page_size(),
                        "page": page,
                    }
        logger.warning("Element nicht gefunden: %s", search_string)
        return None

    def open_navigation(self):
        try:
            logger.info("Öffne Navigation...")
            self._selenium_client.click(
                by=self._config.selenium.navigation.locator_strategie,
                selector=self._config.selenium.navigation.selector,
            )
            logger.debug("Warte auf Navigation...")
            self._selenium_client.wait_for_element(
                self._config.selenium.table_name.locator_strategie,
                self._config.selenium.table_name.selector,
            )
        except Exception as e:
            logger.error("Navigation öffnen fehlgeschlagen: %s", str(e))
            return False

    def open_table(self):
        try:
            logger.info("Öffne Tabelle...")
            self._selenium_client.click(
                by=self._config.selenium.table_name.locator_strategie,
                selector=self._config.selenium.table_name.selector,
            )
            logger.debug("Warte auf Tabelle...")
            self._wait_for_table()
        except Exception as e:
            logger.error("Tabelle öffnen fehlgeschlagen: %s", str(e))
            return False

    def next_page(self):
        logger.debug("Gehe zur nächsten Seite...")
        self._selenium_client.click(
            self._config.selenium.next_page_button.locator_strategie,
            self._config.selenium.next_page_button.selector,
        )
        self._wait_for_table()

    def get_nr_pages(self) -> int:
        pages = int(
            self._selenium_client.find_element(
                by=self._config.selenium.nr_pages.locator_strategie,
                selector=self._config.selenium.nr_pages.selector,
            ).text
        )
        logger.debug("Anzahl Seiten: %d", pages)
        return pages

    def set_page(self, nr):
        logger.info("Setze Seite auf: %d", nr)
        self._selenium_client.type_text(
            by=self._config.selenium.set_page.locator_strategie,
            selector=self._config.selenium.set_page.selector,
            text=str(nr),
            send_return=True,
        )
        self._wait_for_table()
        time.sleep(1)

    def get_page_size(self):
        size = int(
            self._selenium_client.get_select_element(
                by=self._config.selenium.page_size_selector.locator_strategie,
                selector=self._config.selenium.page_size_selector.selector,
            )
        )
        logger.debug("Seitengröße: %d", size)
        return size

    def set_page_size(self, size: str):
        logger.debug("Setze Seitengröße auf: %s", size)
        self._selenium_client.set_select_element(
            self._config.selenium.page_size_selector.locator_strategie,
            self._config.selenium.page_size_selector.selector,
            size,
        )
        self._wait_for_table()

    def _wait_for_table(self):
        logger.debug("Warte auf das Laden der Tabelle...")
        self._selenium_client.wait_for_visibility(
            self._config.selenium.load_table_indicator.locator_strategie,
            self._config.selenium.load_table_indicator.selector,
        )
        self._selenium_client.wait_for_invisibility(
            self._config.selenium.load_table_indicator.locator_strategie,
            self._config.selenium.load_table_indicator.selector,
        )
        self._selenium_client.wait_for_element(
            self._config.selenium.table_element.locator_strategie,
            self._config.selenium.table_element.selector,
        )

    def _replace_in_dict(self, data, search, replace):
        if isinstance(data, dict):
            return {
                k: self._replace_in_dict(v, search, replace) for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._replace_in_dict(i, search, replace) for i in data]
        elif isinstance(data, str):
            return data.replace(search, replace)
        else:
            return data

    def _dict_to_namespace(self, d):
        if isinstance(d, dict):
            return SimpleNamespace(
                **{k: self._dict_to_namespace(v) for k, v in d.items()}
            )
        elif isinstance(d, list):
            return [self._dict_to_namespace(i) for i in d]
        return d

    def _get_config_path(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "config.yaml")
