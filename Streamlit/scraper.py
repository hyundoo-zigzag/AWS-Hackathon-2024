import requests
from bs4 import BeautifulSoup
from utils import clean_title
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
        try:
            google_search = self.driver.find_element(By.CSS_SELECTOR, "div.wNPKTe")
            name = google_search.find_element(By.XPATH, "..").find_element(By.CSS_SELECTOR, "h2").text
            google_search.click()
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[-1])
            return name
        except:
            # 반환값이 없을 때 수행할 코드
            image_titles = []
            title_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.UAiK1e")  # 제목 요소 CSS 선택자 지정
            # 상단 20개의 이미지 제목 수집
            for _, title_element in enumerate(title_elements[:20]):
                title_text = title_element.text
                cleaned_text = clean_title(title_text)  # 불필요한 정보 제거
                image_titles.append(cleaned_text)
            return image_titles
    
    def text_search(self, query):
        self.driver.get(f'https://www.google.com/search?q={query}')

    def crawl_info(self, query):
        try:
            wiki = self.driver.find_element(By.CSS_SELECTOR, "div[data-attrid='description']")
            wiki_url = wiki.find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href')
            content = self.crawl_wiki(wiki_url)
        except:
            try:
                content = self.crawl_wiki(f'https://ko.wikipedia.org/wiki/{query}')
            except:
                content = self.crawl_documents()
        return content
    
    def crawl_documents(self):
        document_area = self.driver.find_element(By.CSS_SELECTOR, "div[id='kp-wp-tab-overview']")
        documents = document_area.find_elements(By.CSS_SELECTOR, "h3.LC20lb")[:5]    # 5개 페이지만 크롤링
        urls = [doc.find_element(By.XPATH, "..").get_attribute('href') for doc in documents]
        print('url :', self.driver.current_url)
        print("urls :", urls)
        texts = list()
        for url in urls:
            try:
                texts.append(
                    BeautifulSoup(requests.get(url).text).get_text(strip=True)
                )
            except:
                continue
        content = '\n\n'.join(texts)
        return content
    
    def crawl_wiki(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text)
        content = soup.find('div', {"id":"mw-content-text"}).text.strip()
        return content