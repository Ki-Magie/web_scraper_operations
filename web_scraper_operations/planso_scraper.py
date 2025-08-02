import logging
from types import SimpleNamespace
import requests
import yaml
import time

from request_client import RequestClient
from selenium_client import SeleniumClient

# Logging wird im Docker main (app.py) definiert
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

planso_username = "touch"
planso_password = "m0n1t0r"


class PlanSoMain:
    """
    Diese Klasse verwenden selenium scraping um die Planso datenbank zu bearbeiten.
    planSo muss erzeugt werden und dann können einzelne flows (z.b. planso_upload_flow)
    mit entsprechenden args gestartet werden.

    in der config sind viele planso speziefische informationen gespeichert. falls sich etwas
    an PlanSo ändert oder wir das ganze für einen anderen kunden verwenden wollen müssen wir
    die config anpassen.
    """

    def __init__(
        self,
        username: str,
        password: str,
        table: str = "25704",
        table_name: str = "Auftragsplanung",
        config: str = "config.yaml",
        client: str = "jvg",
    ):
        self._load_cofig(config, client)
        self._config = self._replace_in_dict(self._config, "TABLE_ID", table)
        self._config = self._replace_in_dict(self._config, "TABLE_NAME", table_name)
        self._config = self._dict_to_namespace(self._config)

        self._selenium_client = SeleniumClient()

        self._config.login_payload.system_login_username = username
        self._config.login_payload.system_login_password = password

        # print(self._config)

    def planso_upload_flow(self, path="/Users/paul/Downloads/weitere_test_datei.pdf"):
        self._selenium_client.open_url(url=self._config.base_url)
        self.login()
        self.open_navigation()
        self.open_table()
        time.sleep(0.5)
        row_info = self.find_element()
        self.upload_file(path, row_info)
        self._selenium_client.click(
            by=self._config.selenium.upload_dialog_close.locator_strategie,
            selector=self._config.selenium.upload_dialog_close.selector,
        )
        time.sleep(0.5)
        self.logout()

    def _load_cofig(self, config: str, client: str):
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

            logger.info("Warte auf Login-Bestätigung...")
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
            logger.error(f"Login fehlgeschlagen: {e}")
            return False

    def logout(self):
        self._selenium_client.open_url(url=self._config.logout_url)

    def upload_file(self, path, row_info, target_field="Dokumente"):
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
                for idx, td in enumerate(tds):
                    td_id = td.get_attribute("aria-describedby")

                    if td_id == getattr(self._config.table_fields, target_field):
                        target_field_idx = idx + 1
                        print(target_field, "hat den index", target_field_idx)
            if row_info["plate"] in row.text:
                upload_cell = row.find_element(
                    self._config.selenium.upload_cell_prepare.locator_strategie,
                    self._config.selenium.upload_cell_prepare.selector
                    + f"[{target_field_idx}]",
                )
                upload_cell.click()
                time.sleep(0.5)
                break
        # nach klick nochmal alles holen
        rows = self._selenium_client.find_elements(
            by=self._config.selenium.rows_of_table.locator_strategie,
            selector=self._config.selenium.rows_of_table.selector,
        )
        for idx, row in enumerate(rows):
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
                return True
        return False

    def find_element(
        self,
        field_name: str = "Kennzeichen",
        search_string: str = "A-BC 123",
    ):
        self._config.find_element.selector = self._config.find_element.selector.replace(
            "FIELD_STRING", field_name
        )
        # Set rows per page?

        nr_pages = self.get_nr_pages()
        field_idx = -1
        for page in range(1, nr_pages + 1):
            # Alle Zeilen der Tabelle holen (z.B. tbody > tr)
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
                    for idx, td in enumerate(tds):
                        td_id = td.get_attribute("aria-describedby")

                        if td_id == getattr(self._config.table_fields, field_name):
                            field_idx = idx
                if search_string in row.text:
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
                    return {
                        "Zeile": idx,
                        "ID": id_nr,
                        "plate": numberplate,
                        "field_idx": field_idx,
                        "page_size": self.get_page_size(),
                        "page": page,
                    }
            if page + 1 == nr_pages:
                break
            self.set_page(page + 1)

    def open_navigation(self):
        try:
            logger.info("öffne navigation")

            self._selenium_client.click(
                by=self._config.selenium.navigation.locator_strategie,
                selector=self._config.selenium.navigation.selector,
            )

            logger.info("Warte auf navigation...")
            self._selenium_client.wait_for_element(
                self._config.selenium.table_name.locator_strategie,
                self._config.selenium.table_name.selector,
            )
        except Exception as e:
            logger.error(f"navigation öffnen fehlgeschlagen: {e}")
            return False

    def open_table(self):
        try:
            logger.info("öffne Tabelle")

            self._selenium_client.click(
                by=self._config.selenium.table_name.locator_strategie,
                selector=self._config.selenium.table_name.selector,
            )

            logger.info("Warte auf Tabelle...")
            self._wait_for_table()

        except Exception as e:
            logger.error(f"Tabelle öffnen fehlgeschlagen: {e}")
            return False

    def next_page(self):
        self._selenium_client.click(
            self._config.selenium.next_page_button.locator_strategie,
            self._config.selenium.next_page_button.selector,
        )
        self._wait_for_table()

    def get_nr_pages(self) -> int:
        return int(
            self._selenium_client.find_element(
                by=self._config.selenium.nr_pages.locator_strategie,
                selector=self._config.selenium.nr_pages.selector,
            ).text
        )

    def set_page(self, nr):
        self._selenium_client.type_text(
            by=self._config.selenium.set_page.locator_strategie,
            selector=self._config.selenium.set_page.selector,
            text=str(nr),
            send_return=True,
        )
        self._wait_for_table()

    def get_page_size(self):
        return int(
            self._selenium_client.get_select_element(
                by=self._config.selenium.page_size_selector.locator_strategie,
                selector=self._config.selenium.page_size_selector.selector,
            )
        )

    def set_page_size(self, size: str):
        self._selenium_client.set_select_element(
            self._config.selenium.page_size_selector.locator_strategie,
            self._config.selenium.page_size_selector.selector,
            size,
        )
        self._wait_for_table()

    def open_upload_dialog(self):
        self._selenium_client.click

    def _wait_for_table(self):
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


planso = PlanSoMain(username="touch", password="m0n1t0r")
planso.planso_flow()
time.sleep(5)
