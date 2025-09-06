import logging
import time
import tempfile
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# Logging wird im Docker main (app.py) definiert
logger = logging.getLogger(__name__)

STRATEGY_MAP = {
    "id": By.ID,
    "xpath": By.XPATH,
    "css": By.CSS_SELECTOR,
    "class": By.CLASS_NAME,
    "name": By.NAME,
    "tag": By.TAG_NAME,
    "link": By.LINK_TEXT,
    "partial_link": By.PARTIAL_LINK_TEXT,
}


class SeleniumClient:
    def __init__(self, headless=True):
        self._profile_dir = tempfile.mkdtemp(prefix="selenium_profile_")
        logger.info("Initialisiere SeleniumClient '%s', (headless=%s)", self._profile_dir, headless)
        
        self._webdriver_wait = 30  # seconds unil timeout

        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self._profile_dir}")
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        prefs = {
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(service=Service(), options=chrome_options)
        self.driver.set_page_load_timeout(self._webdriver_wait)
        self.driver.set_script_timeout(self._webdriver_wait)
        self.wait = WebDriverWait(self.driver, self._webdriver_wait)
        logger.debug("Selenium WebDriver erfolgreich gestartet.")

    def open_url(self, url):
        logger.info("Öffne URL: %s", url)
        self.driver.get(url)

    def type_text(self, by, selector, text, send_return=False):
        logger.debug("Tippe Text in Feld [%s=%s]", by, selector)
        field = self.wait.until(
            EC.presence_of_element_located((STRATEGY_MAP[by], selector))
        )
        field.clear()
        field.send_keys(text)
        if send_return:
            field.send_keys(Keys.RETURN)

    def click(self, by, selector, element=None):
        logger.debug("Klicke auf Element [%s=%s]", by, selector)
        if element:
            details_button = element.find_element(
                STRATEGY_MAP[by],
                selector
            )
            details_button.click()
            return
        button = self.wait.until(
            EC.element_to_be_clickable((STRATEGY_MAP[by], selector))
        )
        button.click()

    def safe_click(self, by, selector, timeout=10):
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                self.click(by, selector)
                return
            except ElementClickInterceptedException:
                # Etwas blockiert den Klick – kurz warten und nochmal versuchen
                time.sleep(0.5)
        raise Exception(f"Konnte Element {selector} nicht klicken – immer blockiert")

    def set_select_element(self, by, selector, value: str):
        logger.info("Setze Select-Element [%s=%s] auf Wert '%s'", by, selector, value)
        select_element = self.wait.until(
            EC.presence_of_element_located((STRATEGY_MAP[by], selector))
        )
        select = Select(select_element)
        select.select_by_value(value)
        logger.info("OK")

    def get_select_element(self, by, selector):
        logger.debug("Lese ausgewählten Wert aus Select-Element [%s=%s]", by, selector)
        select_elem = self.driver.find_element(STRATEGY_MAP[by], selector)
        select = Select(select_elem)
        value = select.first_selected_option.get_attribute("value")
        logger.debug("Aktuell ausgewählter Wert: %s", value)
        return value
    
    def wait_for_all_elements(self, by, selector, timeout=10, return_status=False):
        """
        Wartet auf Elemente oder alternative Fallbacks.

        Parameter:
        ----------
        by : str | list[str]
            Ein einzelner By-String oder eine Liste von By-Strings.
        selector : str | list[str]
            Ein einzelner Selector oder eine Liste von Selectors.
        timeout : int
            Maximale Wartezeit in Sekunden.
        return_status : bool
            Wenn True, wird zusätzlich der Index des getriggerten Selectors zurückgegeben.

        Rückgabe:
        ---------
        list[WebElement] | (list[WebElement], int) | []
        """
        logger.info("Warte auf alle Elemente [%s, %s]", by, selector)

        # Typvalidierung
        if isinstance(by, str) and isinstance(selector, str):
            by = [by]
            selector = [selector]
        elif isinstance(by, list) and isinstance(selector, list):
            if len(by) != len(selector):
                raise ValueError("Die Länge von 'by' und 'selector' muss übereinstimmen")
        else:
            raise ValueError("'by' und 'selector' müssen entweder beide str oder beide list sein.")

        def check(driver):
            for i in range(len(by)):
                elements = driver.find_elements(STRATEGY_MAP[by[i]], selector[i])
                if elements and elements[0].is_displayed():
                    return elements, i
            return False

        try:
            elements, matched_index = self.wait.until(check)
        except TimeoutException:
            logger.warning("Timeout beim Warten auf Elemente: %s", selector)
            return ([], -1) if return_status else []

        logger.info("Gefundene Elemente: %d (Selector: %s)", len(elements), selector[matched_index])
        return (elements, matched_index) if return_status else elements

    def wait_for_element(self, by, selector):
        logger.debug("Warte auf Element [%s=%s]", by, selector)
        self.wait.until(EC.presence_of_element_located((STRATEGY_MAP[by], selector)))

    def wait_for_visibility(self, by, selector):
        logger.info("Warte auf Sichtbarkeit von [%s=%s]", by, selector)
        self.wait.until(EC.visibility_of_element_located((STRATEGY_MAP[by], selector)))

    def wait_for_invisibility(self, by, selector):
        logger.debug("Warte auf Unsichtbarkeit von [%s=%s]", by, selector)
        self.wait.until(
            EC.invisibility_of_element_located((STRATEGY_MAP[by], selector))
        )

    def wait_until_not(self, by, selector):
        logger.debug("Warte bis Element [%s=%s] nicht mehr vorhanden ist", by, selector)
        self.wait.until_not(
            EC.presence_of_element_located((STRATEGY_MAP[by], selector))
        )

    def find_elements(self, by, selector, element=None):
        logger.debug("Finde mehrere Elemente [%s=%s]", by, selector)
        if element is not None:
            return element.find_elements(STRATEGY_MAP[by], selector)
        return self.driver.find_elements(STRATEGY_MAP[by], selector)

    def find_element(self, by, selector, element=None):
        logger.debug("Finde einzelnes Element [%s=%s]", by, selector)
        if element is None:
            return self.driver.find_element(STRATEGY_MAP[by], selector)
        return element.find_element(STRATEGY_MAP[by], selector)

    def execute_script(self, execute_script):
        self.driver.execute_script(execute_script)

    def upload_file(self, element, by, selector, path):
        logger.info("Lade Datei hoch: %s", path)
        file_input = WebDriverWait(element, self._webdriver_wait).until(
            EC.presence_of_element_located((STRATEGY_MAP[by], selector))
        )
        file_input.send_keys(path)
        self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "blockUI")))
        logger.debug("Datei erfolgreich hochgeladen")

    def send_return(self):
        logger.debug("Sende RETURN an aktives Element")
        self.driver.switch_to.active_element.send_keys(Keys.RETURN)

    def quit(self):
        logger.info("Beende WebDriver")
        try:
            self.driver.quit()
        finally:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
