import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
    def __init__(self, headless=False):
        logger.info("Initialisiere SeleniumClient (headless=%s)", headless)
        chrome_options = Options()

        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        prefs = {
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(service=Service(), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
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

    def click(self, by, selector):
        logger.debug("Klicke auf Element [%s=%s]", by, selector)
        button = self.wait.until(
            EC.element_to_be_clickable((STRATEGY_MAP[by], selector))
        )
        button.click()

    def set_select_element(self, by, selector, value: str):
        logger.debug("Setze Select-Element [%s=%s] auf Wert '%s'", by, selector, value)
        select_element = self.wait.until(
            EC.presence_of_element_located((STRATEGY_MAP[by], selector))
        )
        select = Select(select_element)
        select.select_by_value(value)

    def get_select_element(self, by, selector):
        logger.debug("Lese ausgewählten Wert aus Select-Element [%s=%s]", by, selector)
        select_elem = self.driver.find_element(STRATEGY_MAP[by], selector)
        select = Select(select_elem)
        value = select.first_selected_option.get_attribute("value")
        logger.debug("Aktuell ausgewählter Wert: %s", value)
        return value

    def wait_for_element(self, by, selector):
        logger.debug("Warte auf Element [%s=%s]", by, selector)
        self.wait.until(EC.presence_of_element_located((STRATEGY_MAP[by], selector)))

    def wait_for_visibility(self, by, selector):
        logger.debug("Warte auf Sichtbarkeit von [%s=%s]", by, selector)
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

    def upload_file(self, element, by, selector, path):
        logger.info("Lade Datei hoch: %s", path)
        file_input = WebDriverWait(element, 10).until(
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
        self.driver.quit()
