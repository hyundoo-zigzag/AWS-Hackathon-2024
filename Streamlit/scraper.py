import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options


class FierfoxScraper:
    def __init__(self, headless=True):
        self.options = Options()
        if headless:
            self.options.add_argument("-headless")
        self.driver = webdriver.Firefox(options=self.options)
        self.driver.implicitly_wait(10)
    
    def image_search(self, img_file):
        self.driver.get('https://images.google.com/')
        self.driver.find_element(By.CSS_SELECTOR, "div[aria-label='이미지로 검색']").click()
        drag_n_drop_area = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        drag_n_drop_area.send_keys(img_file)
        google_search = self.driver.find_element(By.CSS_SELECTOR, "div.wNPKTe")
        name = google_search.find_element(By.XPATH, "..").find_element(By.CSS_SELECTOR, "h2").text
        google_search.click()
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[-1])
        return name
        
    def crawl_wiki(self):
        wiki = self.driver.find_element(By.CSS_SELECTOR, "div[data-attrid='description']")
        wiki_url = wiki.find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href')
        response = requests.get(wiki_url)
        soup = BeautifulSoup(response.text)
        content = soup.find('div', {"id":"mw-content-text"}).text.strip()
        return content