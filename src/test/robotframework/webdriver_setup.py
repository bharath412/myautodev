from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium import webdriver

def get_webdriver_path():
    return EdgeChromiumDriverManager().install()

def get_options():
    options = webdriver.EdgeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-infobars')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--inprivate')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return options
