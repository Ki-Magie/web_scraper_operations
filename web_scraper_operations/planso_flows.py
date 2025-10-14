import logging
import time

from web_scraper_operations.planso_scraper import PlanSoMain

# Logging-Konfiguration (wird extern in app.py gesetzt)
logger = logging.getLogger(__name__)


def planso_upload_flow(
    field_name: str,
    search_field_name: str,
    search_string: str,
    path: str,
    username: str,
    password: str,
    table: str,
    table_name: str,
    base_url: str = None,
    config: str = None,
    client: str = "jvg",
    headless_mode:bool = True
):
    """
    Vollständiger Ablauf für den Datei-Upload: Login, Navigation, Dateiupload, Logout.
    """
    logger.info("Starte Upload-Flow für Datei: %s", path)

    planso = planso = PlanSoMain(
        username=username, 
        password=password, 
        table=table, 
        table_name=table_name,
        base_url=base_url,
        config=config,
        client=client,
        headless_mode=headless_mode
        )

    try:
        planso.open_base_url()
        planso.login()
        planso.open_navigation()
        planso.open_table()
        time.sleep(1)

        logger.debug("Suche Zielzeile für den Upload...")
        # self.set_page_size(self._page_size)

        # Lädt JEDE seite und schaut ob element da:
        # row_info = self.find_element(search_field_name, search_string)

        # verwendet die Suchfunktion von planso:
        row_info = planso.find_element_with_search(search_field_name, search_string)
        logger.dbug("row found: '%s'", row_info)

        if row_info:
            logger.debug("Starte Datei-Upload...")
            status = planso.upload_file(path, row_info, field_name)
            logger.debug("return of status '%s'", status)
            logger.debug("Schließe Upload-Dialog...")
        else:
            status = f"{search_string} ist nicht im Feld {search_field_name}"
        return {"message": status}
    except Exception as e:
        logger.exception("Error im planso_upload_flow")
        return {"error": "Error im planso_upload_flow"}
    finally:
        try:
            planso.logout()
        except Exception:
            logger.warning("Logout fehlgeschlagen oder planso nicht initialisiert")
        time.sleep(0.3)

def planso_invoice_positions_flow(
    search_field_name: str,
    search_string: str,
    username: str,
    password: str,
    table: str ='',
    orga_list_id: str = '',
    base_url: str = None,
    config: str = None,
    client: str = "jvg",
    headless_mode:bool = True
):
    """
    Vollständiger Ablauf zum auslesen von Ersatzteil Positionen bezogen auf ein Nummernschild
    """
    logger.info("Starte Invoice Flow")

    planso = PlanSoMain(
        username=username, 
        password=password, 
        table=table, 
        orga_list_id=orga_list_id,
        base_url=base_url,
        config=config,
        client=client,
        headless_mode=headless_mode
        )
    try:
        planso.open_base_url()
        planso.login()
        planso.open_schnellzugriff()
        planso.open_orga_list()
        time.sleep(1)
        logger.debug("Suche Zielzeile für Details...")
        row_info = planso.find_element_with_search(search_field_name, search_string)
        logger.debug("row found: '%s'", row_info)

        planso.open_details(row_nr=row_info["Zeile"])
        planso.open_teile()
        teile_info = planso.get_teile_info()  # inkl. Gesamtpreis
        return {"parts": teile_info}
    except Exception as e:
        logger.exception("Error im planso_invoice_positions_flow")
        return {"Error": "Error im planso_invoice_positions_flow"}
    finally:
        try:
            planso.logout()
        except Exception:
            logger.warning("Logout fehlgeschlagen oder planso nicht initialisiert")
        time.sleep(0.3)

def planso_spareparts_ok(
    search_field_name: str,
    search_string: str,
    username: str,
    password: str,
    table: str ='',
    orga_list_id: str = '',
    positions: str = '',
    base_url: str = None,
    config: str = None,
    client: str = "jvg",
    headless_mode:bool = True):
    """
    if positions string is '', all positions get checked
    positions = "Positin1;posisiton2" Semilcolon separated

    """
    logger.info("Starte planso_spareparts_ok Flow")

    planso = PlanSoMain(
        username=username, 
        password=password, 
        table=table, 
        orga_list_id=orga_list_id,
        base_url=base_url,
        config=config,
        client=client,
        headless_mode=headless_mode
        )
    try:
        planso.open_base_url()
        planso.login()
        planso.open_schnellzugriff()
        planso.open_orga_list()
        time.sleep(1)
        logger.debug("Suche Zielzeile für Details...")
        row_info = planso.find_element_with_search(search_field_name, search_string)
        logger.debug("row found: '%s'", row_info)
        planso.open_details(row_nr=row_info["Zeile"])
        planso.open_teile()

        # check boxes
        result = planso.check_sparepart_boxes(positions=positions)
        return {"parts": result}
    except Exception as e:
        logger.exception("Error im planso_spareparts_ok")
        return {"Error": "Error im planso_spareparts_ok"}
    finally:
        try:
            planso.logout()
        except Exception:
            logger.warning("Logout fehlgeschlagen oder planso nicht initialisiert")#
        time.sleep(0.3)
    

def planso_trash_documents(
    field_name: str,
    search_field_name: str,
    search_string: str,
    username: str,
    password: str,
    table: str,
    table_name: str,
    base_url: str = None,
    config: str = None,
    client: str = "jvg",
    headless_mode:bool = True
    ):
    """
    Vollständiger Ablauf zum löschen der Dokumente
    """
    logger.info("Starte planso_trash_documents")

    planso = planso = PlanSoMain(
        username=username, 
        password=password, 
        table=table, 
        table_name=table_name,
        base_url=base_url,
        config=config,
        client=client,
        headless_mode=headless_mode
        )
    try:
        planso.open_base_url()
        planso.login()
        planso.open_navigation()
        planso.open_table()
        time.sleep(1)

        logger.debug("Suche Zielzeile für den Upload...")

        # verwendet die Suchfunktion von planso:
        row_info = planso.find_element_with_search(search_field_name, search_string)
        logger.debug("row found: '%s'", row_info)

        if row_info is not None:
            logger.debug("Starte trash...")
            planso.open_dialog(row_info, field_name)
    except Exception as e:
        logger.exception("Error im planso_trash_documents")
        return
    finally:
        try:
            planso.logout()
        except Exception:
            logger.warning("Logout fehlgeschlagen oder planso nicht initialisiert")#
        time.sleep(0.3)