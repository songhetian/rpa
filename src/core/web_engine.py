from playwright.sync_api import sync_playwright
import time

class WebEngine:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def open_url(self, url):
        if not self.page: self.start()
        self.page.goto(url)

    def find_element(self, selector, timeout=5000):
        """在主页面及所有 iframe 中自动查找元素"""
        if not self.page: return None, None
        
        # 1. 尝试在主页面查找
        try:
            el = self.page.wait_for_selector(selector, timeout=2000)
            if el: return self.page, el
        except: pass

        # 2. 尝试在所有 Frame 中递归查找
        for frame in self.page.frames:
            try:
                el = frame.wait_for_selector(selector, timeout=1000)
                if el: return frame, el
            except: continue
        
        return None, None

    def click_element(self, selector, timeout=5000):
        frame, el = self.find_element(selector, timeout)
        if el:
            # 视觉高亮反馈
            try:
                el.evaluate("el => { el.style.outline = '3px solid red'; setTimeout(() => el.style.outline = '', 1000); }")
            except: pass
            el.click()
            return True
        return False

    def input_text(self, selector, text, timeout=5000):
        frame, el = self.find_element(selector, timeout)
        if el:
            el.fill(text)
            return True
        return False

    def screenshot_element(self, selector):
        """对特定网页元素截图并返回字节流"""
        frame, el = self.find_element(selector)
        if el:
            return el.screenshot()
        return None

    def switch_tab(self, index_or_title):
        """切换标签页"""
        if not self.context: return False
        pages = self.context.pages
        if isinstance(index_or_title, int) and index_or_title < len(pages):
            self.page = pages[index_or_title]
            self.page.bring_to_front()
            return True
        # 也可以按标题匹配（略）
        return False

    def get_text(self, selector):
        frame, el = self.find_element(selector)
        return el.inner_text() if el else None

    def extract_list(self, selector):
        if not self.page: return []
        try:
            elements = self.page.query_selector_all(selector)
            return [el.inner_text().strip() for el in elements]
        except: return []

    def inspect_element(self, url):
        """开启交互式元素拾取模式"""
        if not self.page: self.start()
        self.page.goto(url)
        self.page.add_style_tag(content=".rpa-pick { outline: 2px solid #409eff !important; cursor: crosshair !important; }")
        
        selector_found = []
        def on_clicked(info, selector): selector_found.append(selector)
        self.page.expose_binding("onElementClicked", on_clicked)
        
        self.page.evaluate("""() => {
            document.addEventListener('mouseover', e => e.target.classList.add('rpa-pick'), true);
            document.addEventListener('mouseout', e => e.target.classList.remove('rpa-pick'), true);
            document.addEventListener('click', e => {
                e.preventDefault(); e.stopPropagation();
                let path = e.target.tagName.toLowerCase();
                if (e.target.id) path += '#' + e.target.id;
                window.onElementClicked({}, path);
            }, true);
        }""")
        
        start = time.time()
        while not selector_found and time.time() - start < 60:
            self.page.wait_for_timeout(500)
        return selector_found[0] if selector_found else None

    def stop(self):
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()