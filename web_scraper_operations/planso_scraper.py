import os
from urllib.parse import urljoin
import logging
import time
from types import SimpleNamespace
import yaml

from web_scraper_operations.selenium_client import SeleniumClient

# Logging-Konfiguration (wird extern in app.py gesetzt)
logger = logging.getLogger(__name__)


def download_files_from_link(user_name, password, path_link):
    import requests

    login_url = path_link.split(".de")[0] + ".de/app"
    download_url = path_link

    # Login-Daten
    payload = {
        "system_login_username": user_name,
        "system_login_password": password,
        "user_lat": "",
        "user_lng": "",
        "user_accuracy": "",
    }
    # Session starten
    with requests.Session() as s:
        # Login
        r = s.post(login_url, data=payload)
        if r.status_code == 200:
            logger.info("login bei '%s' erfolgreich", login_url)
        else:
            logger.info("Login fehlgeschlagen: '%s'", r.status_code)

        # Datei runterladen
        r = s.get(download_url)
        if r.status_code == 200:
            return r.content
        else:
            logger.info("Download fehlgeschlagen: '%s'", r.status_code)


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
        table: str = "",
        table_name: str = "",
        orga_list_id: str = "",
        base_url: str = None,
        config: str = None,
        client: str = "jvg",
        headless_mode:bool = True
    ):
        logger.info(
            "Initialisiere PlanSoMain mit Table-ID: %s und Client: %s", table, client
        )
        self._headless_mode = headless_mode
        if config is None:
            config = self._get_config_path()

        self._load_cofig(config, client)
        self._config = self._replace_in_dict(self._config, "TABLE_ID", table)
        self._config = self._replace_in_dict(self._config, "TABLE_NAME", table_name)
        self._config = self._replace_in_dict(self._config, "ORGA_LIST_ID", orga_list_id)
        self._config = self._dict_to_namespace(self._config)

        if base_url is not None:
            self._config.base_url = base_url
            self._config.login_url = urljoin(base_url, "app")
            self._config.logout_url = urljoin(base_url, "do?m=logout")

        self._page_size = "100"

        self._selenium_client = SeleniumClient(headless=self._headless_mode)

        # Login-Daten setzen (aus Sicherheitsgründen nicht loggen!)
        self._config.login_payload.system_login_username = username
        self._config.login_payload.system_login_password = password

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

            time.sleep(1)
            logging.debug("Warte dass popup verschwindet")
            self._selenium_client.wait_for_overlay_to_disappear(
                by=self._config.selenium.wait_popup.locator_strategie,
                selector=self._config.selenium.wait_popup.selector
            )

            logger.info("Login erfolgreich.")
            return True

        except Exception as e:
            logger.error("Login fehlgeschlagen: %s", str(e))
            return False

    def logout(self):
        logger.info("Führe Logout durch...")
        self._selenium_client.open_url(url=self._config.logout_url)
        time.sleep(0.5)
        logger.info("Schließe Client")
        self._selenium_client.quit()

    def open_url(self, url):
        self._selenium_client.open_url(url=url)

    def open_base_url(self):
        self.open_url(url=self._config.base_url)
    
    def open_dialog(self, row_info, target_field="Dokumente"):
        self._config.file_upload.selector = self._config.file_upload.selector.replace(
            "SEARCH_FIELD_STRING", target_field
        )
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
                    logger.debug("Klicke trash")
                    dialog_cell = row.find_element(
                        self._config.selenium.upload_cell_prepare.locator_strategie,
                        self._config.selenium.upload_cell_prepare.selector
                        + f"[{target_field_idx}]",
                    )
                    dialog_cell.click()
                    time.sleep(1)
                    break
        except Exception as e:
            logger.error("Trash fehlgeschlagen: %s", str(e))
    
#     def get_files_in_dialog(self):
#         rows = self._selenium_client.wait_unil_presence_located(
#             by=
#             selector=
#         )
# "ul#images_sortable > li.images_draggable"


    def upload_file(self, path, row_info, target_field="Dokumente"):
        logger.info("Starte Datei-Upload für Ziel-Feld: %s", target_field)
        self._config.file_upload.selector = self._config.file_upload.selector.replace(
            "SEARCH_FIELD_STRING", target_field
        )
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
                    time.sleep(1)
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
                    # Warten auf das upload status fenster
                    self._selenium_client.wait_until_not(
                        by=self._config.selenium.status_upload_uploading.locator_strategie,
                        selector=self._config.selenium.status_upload_uploading.selector,
                    )
                    time.sleep(2)
                    # Warten auf das Warnung fenster "datei existiert bereits"
                    if self.check_for_alert():
                        return self.check_overlay_type()

                    self._selenium_client.wait_for_invisibility(
                        by=self._config.selenium.upload_dialog_alert.locator_strategie,
                        selector=self._config.selenium.upload_dialog_alert.selector,
                    )

                    logger.info("Datei erfolgreich hochgeladen.")
                    self._selenium_client.wait_for_invisibility(
                        by=self._config.selenium.wait_for_upload.locator_strategie,
                        selector=self._config.selenium.wait_for_upload.selector,
                    )
                    self._selenium_client.safe_click(
                        by=self._config.selenium.upload_dialog_close.locator_strategie,
                        selector=self._config.selenium.upload_dialog_close.selector,
                    )
                    return "File Upload erfolgreich"
        except Exception as e:
            logger.error("Upload fehlgeschlagen: %s", str(e))
        self._selenium_client.wait_for_invisibility(
            by=self._config.selenium.wait_for_upload.locator_strategie,
            selector=self._config.selenium.wait_for_upload.selector,
        )
        self._selenium_client.safe_click(
            by=self._config.selenium.upload_dialog_close.locator_strategie,
            selector=self._config.selenium.upload_dialog_close.selector,
        )
        return "File not uploaded"

    def find_element(self, field_name: str, search_string: str):
        logger.info(
            "Suche Element mit Feld '%s' und Suchbegriff '%s'",
            field_name,
            search_string,
        )
        self._config.find_element.selector = self._config.find_element.selector.replace(
            "SEARCH_FIELD_STRING", field_name
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
                    logger.info(
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

    def find_element_with_search(self, field_name: str, search_string: str):
        logger.info(
            "Suche Element mit Feld '%s' und Suchbegriff '%s'",
            field_name,
            search_string,
        )
        wait_time = 1
        self._config.selenium.search_field.selector = (
            self._config.selenium.search_field.selector.replace(
                "SEARCH_FIELD_STRING", field_name
            )
        )
        self._config.find_element.selector = self._config.find_element.selector.replace(
            "SEARCH_FIELD_STRING", field_name
        )

        # ----- such operator setzen
        logger.info("setze den such operator auf 'ist gleich'")
        time.sleep(wait_time)
        self._selenium_client.wait_for_element(
            self._config.selenium.search_field.locator_strategie,
            self._config.selenium.search_field.selector,
        )
        time.sleep(wait_time)
        spalten_element = self._selenium_client.find_element(
            self._config.selenium.search_field.locator_strategie,
            self._config.selenium.search_field.selector,
        )
        time.sleep(wait_time)
        search_button = self._selenium_client.find_element(
            self._config.selenium.search_strategy_menu.locator_strategie,
            self._config.selenium.search_strategy_menu.selector,
            spalten_element,
        )
        time.sleep(wait_time)
        search_button.click()
        time.sleep(wait_time)
        self._selenium_client.click(
            self._config.selenium.search_strategy.locator_strategie,
            self._config.selenium.search_strategy.selector,
        )
        time.sleep(wait_time)

        # ----- setze den such string
        logger.info("setze den suchstring '%s'", search_string)
        self._selenium_client.wait_for_visibility(
            self._config.selenium.search_field.locator_strategie,
            self._config.selenium.search_field.selector,
        )
        time.sleep(wait_time)
        self._selenium_client.type_text(
            self._config.selenium.search_field.locator_strategie,
            self._config.selenium.search_field.selector,
            search_string,
        )
        time.sleep(wait_time)

        # -----
        page = 1
        field_idx = -1
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
                logger.info(
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

    def open_schnellzugriff(self):
        try:
            logger.info("Öffne Schnellzugriff...")
            self._selenium_client.click(
                by=self._config.selenium.schnellzugriff.locator_strategie,
                selector=self._config.selenium.schnellzugriff.selector,
            )
        except Exception as e:
            logger.error("Schnellzugriff öffnen fehlgeschlagen: %s", str(e))
            return False

    def open_table(self):
        try:
            logger.info("Öffne Tabelle...")
            self._selenium_client.click(
                by=self._config.selenium.table_name.locator_strategie,
                selector=self._config.selenium.table_name.selector,
            )
            # self._wait_for_table()
            time.sleep(1)
        except Exception as e:
            logger.error("Tabelle öffnen fehlgeschlagen: %s", str(e))
            return False

    def open_orga_list(self):
        try:
            logger.info("Öffne Orga Liste...")
            self._selenium_client.click(
                by=self._config.selenium.orga_list.locator_strategie,
                selector=self._config.selenium.orga_list.selector,
            )
            logger.info("Warte auf Orga Liste...")
            self._wait_for_orga_list()
        except Exception as e:
            logger.error("Tabelle öffnen fehlgeschlagen: %s", str(e))
            return False

    def open_details(self, row_nr):
        try:
            wait = 1
            logger.info("Öffne Details...")
            self._selenium_client.wait_for_visibility(
                by=self._config.selenium.details_button.locator_strategie,
                selector=self._config.selenium.details_button.selector_row
                + f"[{row_nr}]",
            )
            time.sleep(wait)
            row = self._selenium_client.find_element(
                by=self._config.selenium.details_button.locator_strategie,
                selector=self._config.selenium.details_button.selector_row
                + f"[{row_nr}]",
            )
            time.sleep(wait)
            self._selenium_client.click(
                by=self._config.selenium.details_button.locator_strategie,
                selector=self._config.selenium.details_button.selector,
                element=row,
            )
            time.sleep(wait)
            # self._wait_for_table()
        except Exception as e:
            logger.error("Details öffnen fehlgeschlagen: %s", str(e))
            return False

    def open_teile(self):
        try:
            logger.info("Öffne Teile...")
            self._selenium_client.click(
                by=self._config.selenium.teile_button.locator_strategie,
                selector=self._config.selenium.teile_button.selector,
            )
        except Exception as e:
            logger.error("Teile öffnen fehlgeschlagen: %s", str(e))
            return False

    def next_page(self):
        logger.debug("Gehe zur nächsten Seite...")
        self._selenium_client.click(
            self._config.selenium.next_page_button.locator_strategie,
            self._config.selenium.next_page_button.selector,
        )
        self._wait_for_table()

    def get_nr_pages(self) -> int:
        timeout = 10
        self._selenium_client.wait_for_element(
            self._config.selenium.nr_pages.locator_strategie,
            self._config.selenium.nr_pages.selector,
        )
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                text = self._selenium_client.find_element(
                    by=self._config.selenium.nr_pages.locator_strategie,
                    selector=self._config.selenium.nr_pages.selector,
                ).text
                if text != "":
                    logging.info("number page: %d", text)
                    return int(text)
                time.sleep(0.5)
            except:
                time.sleep(0.5)
        raise Exception(f"get_nr_page fehlgeschlagen")

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

    def get_teile_info(self):
        try:
            logger.info("Lese Teile Infos")
            time.sleep(1)
            # self._selenium_client.wait_for_visibility(
            #     by=self._config.selenium.teile_elements.locator_strategie,
            #     selector=self._config.selenium.teile_elements.selector,
            # )
            logger.debug("wait_for_all_elements")
            rows, matched_selector = self._selenium_client.wait_for_all_elements(
                by=[
                    self._config.selenium.teile_elements.locator_strategie,
                    self._config.selenium.keine_teile.locator_strategie,
                ],
                selector=[
                    self._config.selenium.teile_elements.selector,
                    self._config.selenium.keine_teile.selector,
                ],
                return_status=True
            )
            if matched_selector == 1:
                logger.info("Keine Ersatzteile vorhanden.")
                return []

            # 3. Tabelle auslesen
            parts_data = []

            for row in rows:
                part = {}
                logger.debug(f"{row}")
                logger.debug("lese data_id")
                part["data_id"] = row.get_attribute("data-id")
                logger.debug("lese data_partid")
                part["data_partid"] = row.get_attribute("data-partid")
                logger.debug("lese data_pnum")
                part["data_pnum"] = row.get_attribute("data-pnum")
                logger.debug("lese name")
                try:
                    part["name"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.name,
                        element=row,
                    ).text.strip()
                except:
                    part["name"] = None
                logger.debug("lese part_number")
                try:
                    part["part_number"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.part_nr,
                        element=row,
                    ).get_attribute("data-prtnumber")
                except:
                    part["part_number"] = None
                logger.debug("lese price")
                try:
                    part["price"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.price,
                        element=row,
                    ).text.strip()
                except:
                    part["price"] = None
                logger.debug("lese quantity")
                try:
                    part["quantity"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.quantity,
                        element=row,
                    ).text.strip()
                except:
                    part["quantity"] = None
                logger.debug("lese total_price")
                try:
                    part["total_price"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.total_price,
                        element=row,
                    ).text.strip()
                except:
                    part["total_price"] = None
                logger.debug("lese bestellt")
                try:
                    part["bestellt"] = (
                        self._selenium_client.find_element(
                            by=self._config.teile_tabelle.locator_strategie,
                            selector=self._config.teile_tabelle.bestellt,
                            element=row,
                        ).get_attribute("checked")
                        is not None
                    )
                except:
                    part["bestellt"] = None
                logger.debug("lese delivered")
                try:
                    part["delivered"] = (
                        self._selenium_client.find_element(
                            by=self._config.teile_tabelle.locator_strategie,
                            selector=self._config.teile_tabelle.delivered,
                            element=row,
                        ).get_attribute("checked")
                        is not None
                    )
                except:
                    part["delivered"] = None
                logger.debug("lese status")
                try:
                    part["status"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.status,
                        element=row,
                    ).get_attribute("title")
                except:
                    part["status"]=None
                logger.debug("lese bestelldatum")
                try:
                    part["bestelldatum"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.bestelldatum,
                        element=row,
                    ).text.strip()
                except:
                    part["bestelldatum"] = None
                logger.debug("lese project_num")
                try:
                    part["project_num"] = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.project_num,
                        element=row,
                    ).text.strip()
                except:
                    part["project_num"] = None
                logger.debug(f"part: {part}")
                parts_data.append(part)

            num = []
            for p in parts_data:
                if not p["project_num"] in num:
                    num.append(p["project_num"])

            logger.debug(f"ersatzteile gedunden: {parts_data}")
            
            # Gesamtpreis und ersatzteile_summe
            try:
                table = self._selenium_client.wait_for_all_elements(
                    by=self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie,
                    selector=self._config.teile_tabelle.bottom_line_gesamtpreis.selector
                )[0]  # nur eine Tabelle
            except Exception as e:
                logger.warning(f"Gesamtpreis Tabelle konnte nicht gefunden werden: {e}")
            
            gesamtpreis = None
            ersatzteile_summe = None
            for i, auftragsnummer in enumerate(num):
                try:
                    first_row = self._selenium_client.find_elements(
                        by=self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag,
                        selector=self._config.teile_tabelle.bottom_line_gesamtpreis.selector_tr,
                        element=table
                    )[i]
                    ersatzteile_summe_td = self._selenium_client.find_elements(
                        by=self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag,
                        selector=self._config.teile_tabelle.bottom_line_gesamtpreis.selector_td,
                        element=first_row
                    )[1]
                    ersatzteile_summe = ersatzteile_summe_td.text.replace("€", "").replace(",", ".").strip()
                except Exception as e:
                    logger.warning(f"Ersatzteile Summe konnte nicht ausgelesen werden: {e}")
                parts_data.append({f"{auftragsnummer} ersatzteile_summe": ersatzteile_summe})

            try:
                last_row = self._selenium_client.find_elements(
                    by=self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag,
                    selector=self._config.teile_tabelle.bottom_line_gesamtpreis.selector_tr,
                    element=table
                )[-1]
                gesamtpreis_td = self._selenium_client.find_elements(
                    by=self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag,
                    selector=self._config.teile_tabelle.bottom_line_gesamtpreis.selector_td,
                    element=last_row
                )[-1]
                gesamtpreis = gesamtpreis_td.text.strip()

                # last_row = table.find_elements(self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag, "tr")[-1]
                # gesamtpreis_td = last_row.find_elements(self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag, "td")[-1]
                # gesamtpreis = gesamtpreis_td.find_element(self._config.teile_tabelle.bottom_line_gesamtpreis.locator_strategie_tag, "b").text.strip()
            except Exception as e:
                logger.warning(f"Gesamtpreis konnte nicht ausgelesen werden: {e}")
            parts_data.append({"gesamtpreis": gesamtpreis})

            return parts_data
        except Exception as e:
            logger.error("Teile Infos auslesen fehlgeschlagen: %s", str(e))
            return []
    
    def check_sparepart_boxes(self, positions: str=''):
        try:
            logger.info("checke Ersatzteil check boxen")
            time.sleep(1)
            # self._selenium_client.wait_for_visibility(
            #     by=self._config.selenium.teile_elements.locator_strategie,
            #     selector=self._config.selenium.teile_elements.selector,
            # )
            pos_array = positions.split(';') if positions else []
            logger.info("wait_for_all_elements")
            rows, matched_selector = self._selenium_client.wait_for_all_elements(
                by=[
                    self._config.selenium.teile_elements.locator_strategie,
                    self._config.selenium.keine_teile.locator_strategie,
                ],
                selector=[
                    self._config.selenium.teile_elements.selector,
                    self._config.selenium.keine_teile.selector,
                ],
                return_status=True
            )
            if matched_selector == 1:
                logger.info("Keine Ersatzteile vorhanden.")
                return []

            # zeilen durchgehen:
            checked = {}
            for row in rows:
                try:
                    logger.info("lese name")
                    part_name = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.name,
                        element=row,
                    ).text.strip()
                    logger.info("lese part_number")
                    part_number = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.locator_strategie,
                        selector=self._config.teile_tabelle.part_nr,
                        element=row,
                    ).get_attribute("data-prtnumber")
                    
                    run = False
                    if pos_array == []:
                        run = True
                    elif part_number in pos_array:
                        run = True
                    elif part_name in pos_array:
                        run = True
                    if run:
                        checkbox = self._selenium_client.find_element(
                        by=self._config.teile_tabelle.price_checkbox.locator_strategie,
                        selector=self._config.teile_tabelle.price_checkbox.selector,
                        element=row,
                        )
                        time.sleep(0.5)
                        if not checkbox.is_selected():
                            logger.info(f"checking price_checkbox for {part_name}")

                            self._selenium_client.execute_script("""
                            arguments[0].checked = true;
                            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                            """, checkbox)
                            # checkbox.click()
                            checked[part_name] = "checked"
                        else:
                            checked[part_name] = "already checked"
                except Exception as e:
                    logger.warning(f"checkbox checken fehlgeschlagen: {e}")

            return checked    
        except Exception as e:
            logger.error("Checkboxen checken fehlgeschlagen: %s", str(e))
            return {"error: Checkboxen checken fehlgeschlagen"}



    def check_for_alert(self):
        try:
            self._selenium_client.wait_for_visibility(
                self._config.selenium.upload_dialog_alert.locator_strategie,
                self._config.selenium.upload_dialog_alert.selector,
            )
            return True
        except:
            return False

    def check_overlay_type(self):
        try:
            overlay_elem = self._selenium_client.find_element(
                self._config.selenium.wait_for_upload.locator_strategie,
                self._config.selenium.wait_for_upload.selector,
            )
            if overlay_elem.is_displayed():
                text = overlay_elem.text.strip().lower()
                logging.info(f"Overlay erkannt: {text}")

                if "upload" in text or "wird hochgeladen" in text:
                    return "upload"
                elif (
                    "das bild konnte nicht hochgeladen werden" in text
                    or "alert" in text
                    or "nicht möglich" in text
                ):
                    return "File existiert bereits"
                else:
                    return "unbekannt"
        except:
            logging.info("error in check_overlay_type")
            return None

    def _wait_for_table(self):
        logger.info("Warte auf das Laden der Tabelle...")
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

    def _wait_for_orga_list(self):
        logger.debug("Warte auf das Laden der Orga Liste...")
        self._selenium_client.wait_for_visibility(
            self._config.selenium.load_table_indicator.locator_strategie,
            self._config.selenium.load_table_indicator.selector,
        )
        self._selenium_client.wait_for_invisibility(
            self._config.selenium.load_table_indicator.locator_strategie,
            self._config.selenium.load_table_indicator.selector,
        )
        self._selenium_client.wait_for_element(
            self._config.selenium.orga_list_element.locator_strategie,
            self._config.selenium.orga_list_element.selector,
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
