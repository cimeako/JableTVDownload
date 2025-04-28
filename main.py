# author: hcjohn463
#!/usr/bin/env python
# coding: utf-8

# --- Original main.py imports ---
from args import get_parser, av_recommand  # Modified import
from download import download
from movies import movieLinks

# --- Imports from getList.py ---
import time
import os
import re
import sqlite3
import sys
import datetime
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog

# Selenium 相關導入 (Ensure these are installed: pip install selenium webdriver-manager beautifulsoup4)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告：未找到 Selenium 或相關組件。爬取功能將不可用。")
    print("請執行 'pip install selenium webdriver-manager beautifulsoup4' 來安裝。")

# --- Settings from getList.py ---
# 資料庫設定 (使用相對路徑)
DB_PATH = "test.db"

# URL 模板
URL_TEMPLATES = {
    "latest": "https://jable.tv/latest-updates/?mode=async&function=get_block&block_id=list_videos_latest_videos_list&sort_by=post_date&from=",
    "actress": "https://jable.tv/models/{}/?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from=",
    "category": "https://jable.tv/categories/{}/?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from=",
    "tag": "https://jable.tv/tags/{}/?mode=async&function=get_block&block_id=list_videos_common_videos_list&sort_by=post_date&from=",
}

# 預設值
DEFAULT_VALUES = {"actress": "kana-mito", "category": "chinese-subtitle", "tag": "ol"}

# 常見選項
COMMON_OPTIONS = {
    "category": {
        "chinese-subtitle": "中文字幕",
        "pantyhose": "絲襪美腿",
        "uniform": "制服",
    },
    "tag": {"ol": "OL", "black-pantyhose": "黑絲", "beautiful-leg": "美腿"},
}

# --- Functions from getList.py ---


# --- 資料庫相關函數 ---
def setup_database():
    """設置資料庫，如果不存在則創建"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):  # Check if db_dir is not empty
        os.makedirs(db_dir)
        print(f"已創建目錄: {db_dir}")

    conn = sqlite3.connect(DB_PATH)
    print(f"已連接到資料庫: {DB_PATH}")
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS av_db (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fanhao TEXT UNIQUE,
        url TEXT,
        title TEXT,
        crawl_date TEXT,
        crawl_type TEXT,
        crawl_value TEXT
    )
    """
    )
    conn.commit()
    return conn, cursor


def check_db_structure(conn, cursor):
    """檢查資料庫結構"""
    cursor.execute("PRAGMA table_info(av_db)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    if "crawl_date" not in column_names:
        print("添加 crawl_date 欄位到資料表")
        cursor.execute("ALTER TABLE av_db ADD COLUMN crawl_date TEXT")
        conn.commit()
    if "crawl_type" not in column_names:
        print("添加 crawl_type 欄位到資料表")
        cursor.execute("ALTER TABLE av_db ADD COLUMN crawl_type TEXT")
        conn.commit()
    if "crawl_value" not in column_names:
        print("添加 crawl_value 欄位到資料表")
        cursor.execute("ALTER TABLE av_db ADD COLUMN crawl_value TEXT")
        conn.commit()


def search_videos_in_python(keyword):
    """在 Python 中進行過濾搜尋"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT fanhao, url, title, crawl_date FROM av_db")
        all_records = cursor.fetchall()
        cursor.close()
        conn.close()

        keyword_lower = keyword.lower()
        results = []
        for record in all_records:
            fanhao, url, title, crawl_date = record
            if (title and keyword_lower in title.lower()) or (
                fanhao and keyword_lower in fanhao.lower()
            ):
                results.append((fanhao, url, title, crawl_date))
        return results
    except Exception as e:
        print(f"搜尋時發生錯誤: {e}")
        return []


def get_latest_videos_from_db(limit=20):  # Renamed to avoid conflict if needed
    """獲取最新的影片（按照收錄日期排序）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fanhao, url, title, crawl_date
            FROM av_db
            ORDER BY crawl_date DESC, id DESC
            LIMIT ?
        """,
            (limit,),
        )
        latest_records = cursor.fetchall()
        cursor.close()
        conn.close()
        return latest_records
    except Exception as e:
        print(f"獲取最新影片時發生錯誤: {e}")
        return []


def export_to_file(keyword, results, is_latest=False):
    """將搜尋結果匯出到檔案"""
    try:
        if is_latest:
            filename = "latest_videos.txt"
            title_line = f"最新收錄的 {len(results)} 部影片"
        else:
            # Sanitize keyword for filename
            safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)
            filename = f"{safe_keyword}.txt"
            title_line = f"關鍵字 '{keyword}' 的搜尋結果"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{title_line}:\n")
            f.write("=" * 80 + "\n\n")
            for i, (fanhao, url, title, crawl_date) in enumerate(results, 1):
                f.write(f"{i}. {title}\n")
                f.write(f"   番號: {fanhao}\n")
                f.write(f"   網址: {url}\n")
                if crawl_date:
                    f.write(f"   收錄日期: {crawl_date}\n")
                f.write("\n")
            f.write("-" * 80 + "\n")
            if is_latest:
                f.write(f"共列出 {len(results)} 個最新收錄的影片\n")
            else:
                f.write(f"共找到 {len(results)} 個符合關鍵字 '{keyword}' 的影片\n")
        print(f"結果已匯出到檔案: {filename}")
        return True
    except Exception as e:
        print(f"匯出檔案時發生錯誤: {e}")
        return False


def print_results(results, keyword=None, is_latest=False):
    """在控制台顯示結果"""
    if not results:
        if is_latest:
            print("資料庫中沒有找到任何影片")
        else:
            print(f"找不到符合關鍵字 '{keyword}' 的影片")
        return

    if is_latest:
        print(f"\n資料庫中最新收錄的 {len(results)} 部影片:")
    else:
        print(f"\n找到 {len(results)} 個符合關鍵字 '{keyword}' 的影片:")
    print("-" * 80)
    for i, (fanhao, url, title, crawl_date) in enumerate(
        results[:10], 1
    ):  # 只顯示前10個
        print(f"{i}. {title}")
        print(f"   番號: {fanhao}")
        if crawl_date:
            print(f"   收錄日期: {crawl_date}")
    if len(results) > 10:
        print(
            f"\n...還有 {len(results) - 10} 個結果未顯示，請查看匯出的檔案以獲取完整列表"
        )


# --- 爬蟲相關函數 ---
def setup_selenium_with_proxy():
    """設置 Selenium 並使用代理 (如果需要)"""
    if not SELENIUM_AVAILABLE:
        print("Selenium 不可用，無法啟動爬蟲。")
        return None

    options = Options()
    # 添加代理設定 (如果需要)
    # proxy = "http://your_proxy_server:port"
    # options.add_argument(f"--proxy-server={proxy}")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"啟動 Selenium 時出錯: {e}")
        print("請確保 Chrome 瀏覽器已安裝，或 ChromeDriver 路徑正確。")
        return None


def get_page_with_selenium(driver, url):
    """使用 Selenium 獲取頁面內容"""
    if not driver:
        return None
    try:
        print(f"正在訪問頁面: {url}")
        driver.get(url)
        time.sleep(5)  # 等待頁面加載 (可能需要調整)
        page_source = driver.page_source
        print("頁面獲取成功")
        # 可以選擇性保存 HTML 以便分析
        # with open(f"jable_page_{time.time()}.html", "w", encoding="utf-8") as f:
        #     f.write(page_source)
        return page_source
    except Exception as e:
        print(f"使用 Selenium 獲取頁面時出錯: {e}")
        return None


def parse_videos(html_content):
    """解析視頻列表"""
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, "html.parser")
    videos = []
    # 檢查是否是 JSON 格式 (AJAX 響應)
    if html_content.strip().startswith("{") and html_content.strip().endswith("}"):
        try:
            json_data = json.loads(html_content)
            if "html" in json_data:
                soup = BeautifulSoup(json_data["html"], "html.parser")
        except json.JSONDecodeError:
            pass  # 不是有效的 JSON，繼續按 HTML 解析

    # 嘗試多種可能的選擇器
    video_containers = soup.select(
        "div.video-img-box, div.col-6.col-sm-4.col-lg-3, div.thumb-overlay"
    )
    print(f"找到 {len(video_containers)} 個視頻容器")

    for container in video_containers:
        try:
            title_element = container.select_one("h6.title a, a.title")
            if title_element:
                title = title_element.text.strip()
                url = title_element.get("href")
                if url:  # 確保 URL 存在
                    path_parts = urlparse(url).path.split("/")
                    # 提取番號，通常是倒數第二個部分
                    fanhao = (
                        path_parts[-2] if len(path_parts) > 2 and path_parts[-2] else ""
                    )
                    if fanhao:  # 確保番號有效
                        videos.append({"f": fanhao, "u": url, "t": title})
        except Exception as e:
            print(f"解析視頻元素時出錯: {e}")
    return videos


def get_existing_fanhaos(cursor):
    """獲取資料庫中已存在的所有番號"""
    cursor.execute("SELECT fanhao FROM av_db")
    return {row[0] for row in cursor.fetchall()}


def save_to_database(
    conn, cursor, videos, existing_fanhaos, crawl_type="latest", crawl_value=""
):
    """保存視頻到資料庫，跳過已存在的番號，並返回是否發現已存在的影片"""
    found_existing = False
    new_videos_count = 0
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    for video in videos:
        fanhao = video.get("f")  # 使用 .get() 避免 KeyError
        if not fanhao or fanhao in existing_fanhaos:
            # print(f"跳過已存在或無效番號: {fanhao}") # 可以取消註釋以顯示更多信息
            if fanhao in existing_fanhaos:
                found_existing = True  # 只有當番號確實存在時才標記
            continue

        try:
            cursor.execute(
                "INSERT INTO av_db (fanhao, url, title, crawl_date, crawl_type, crawl_value) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    fanhao,
                    video.get("u"),
                    video.get("t"),
                    current_date,
                    crawl_type,
                    crawl_value,
                ),
            )
            existing_fanhaos.add(fanhao)
            new_videos_count += 1
            print(f"已保存: {fanhao} - {video.get('t')} - 爬取日期: {current_date}")
        except sqlite3.IntegrityError:
            print(f"番號已存在 (衝突): {fanhao}")
            found_existing = True
        except Exception as e:
            print(f"保存視頻 '{fanhao}' 時出錯: {e}")

    conn.commit()
    print(f"本頁新增了 {new_videos_count} 個新影片")
    return found_existing


def crawl_videos_by_type():
    """根據用戶選擇的類型爬取視頻"""
    if not SELENIUM_AVAILABLE:
        print("Selenium 不可用，無法執行爬取。")
        return

    try:
        conn, cursor = setup_database()
        check_db_structure(conn, cursor)
        existing_fanhaos = get_existing_fanhaos(cursor)
        print(f"資料庫中已有 {len(existing_fanhaos)} 個影片")

        print("\n請選擇爬取類型:")
        print("1. 最新影片")
        print("2. 特定女優")
        print("3. 特定類別")
        print("4. 特定標籤")
        print("0. 返回主選單")
        crawl_type_choice = input("請選擇 (0-4): ").strip()

        if crawl_type_choice == "0":
            cursor.close()
            conn.close()
            return

        url_template = ""
        crawl_type = ""
        crawl_value = ""

        if crawl_type_choice == "1":
            url_template = URL_TEMPLATES["latest"]
            crawl_type = "latest"
        elif crawl_type_choice == "2":
            crawl_type = "actress"
            print(f"\n預設女優: {DEFAULT_VALUES['actress']}")
            crawl_value = (
                input(f"請輸入女優ID (直接按Enter使用預設值): ").strip()
                or DEFAULT_VALUES["actress"]
            )
            url_template = URL_TEMPLATES["actress"].format(crawl_value)
        elif crawl_type_choice == "3":
            crawl_type = "category"
            print("\n常見類別:")
            for key, value in COMMON_OPTIONS["category"].items():
                print(f"- {key}: {value}")
            print(f"\n預設類別: {DEFAULT_VALUES['category']} (中文字幕)")
            crawl_value = (
                input(f"請輸入類別ID (直接按Enter使用預設值): ").strip()
                or DEFAULT_VALUES["category"]
            )
            url_template = URL_TEMPLATES["category"].format(crawl_value)
        elif crawl_type_choice == "4":
            crawl_type = "tag"
            print("\n常見標籤:")
            for key, value in COMMON_OPTIONS["tag"].items():
                print(f"- {key}: {value}")
            print(f"\n預設標籤: {DEFAULT_VALUES['tag']} (OL)")
            crawl_value = (
                input(f"請輸入標籤ID (直接按Enter使用預設值): ").strip()
                or DEFAULT_VALUES["tag"]
            )
            url_template = URL_TEMPLATES["tag"].format(crawl_value)
        else:
            print("無效的選擇，返回主選單")
            cursor.close()
            conn.close()
            return

        max_pages = 0
        while True:
            try:
                pages_input = input(
                    f"請輸入要爬取的頁數 (例如 5，輸入 0 返回): "
                ).strip()
                if not pages_input:
                    continue
                max_pages = int(pages_input)
                if max_pages == 0:
                    cursor.close()
                    conn.close()
                    return
                elif max_pages > 0:
                    break
                else:
                    print("請輸入一個正整數或 0。")
            except ValueError:
                print("輸入無效，請輸入一個數字。")
            except EOFError:
                print("\n檢測到輸入終止符。返回主選單。")
                cursor.close()
                conn.close()
                return

        driver = setup_selenium_with_proxy()
        if not driver:
            cursor.close()
            conn.close()
            return  # Exit if driver setup failed

        try:
            for page in range(1, max_pages + 1):
                page_url = url_template + str(page)
                print(f"\n--- 正在爬取第 {page} 頁 ---")
                html_content = get_page_with_selenium(driver, page_url)
                if not html_content:
                    print(f"無法獲取第 {page} 頁內容，可能需要檢查網路或代理。")
                    continue  # 或 break，取決於是否要繼續嘗試後續頁面

                videos = parse_videos(html_content)
                if videos:
                    found_existing = save_to_database(
                        conn, cursor, videos, existing_fanhaos, crawl_type, crawl_value
                    )
                    # 如果爬取最新影片且遇到已存在的影片，可以選擇停止
                    if crawl_type == "latest" and found_existing:
                        print("檢測到已存在的影片，停止爬取最新影片。")
                        # 可以選擇讓用戶決定是否繼續
                        # continue_choice = input("是否繼續爬取下一頁？(y/n): ").lower()
                        # if continue_choice != 'y':
                        #     break
                        break  # 預設停止
                else:
                    print(f"第 {page} 頁沒有找到視頻")
                    # 可以考慮在此處停止，因為後續頁面可能也沒有內容
                    # continue_choice = input("是否繼續嘗試下一頁？(y/n): ").lower()
                    # if continue_choice != 'y':
                    #     break
                    break  # 預設停止

                time.sleep(2)  # 增加延遲避免過快請求

        finally:
            if driver:
                driver.quit()
            cursor.close()
            conn.close()
            print("\n爬取完成。")

    except Exception as e:
        print(f"爬取過程中發生未預期錯誤: {e}")
        if "conn" in locals() and conn:
            conn.close()
        if "driver" in locals() and driver:
            driver.quit()


# --- 搜尋與列出功能 ---
def search_videos():
    """搜尋資料庫中的影片"""
    keyword = input("請輸入要搜尋的關鍵字 (標題或番號): ").strip()
    if not keyword:
        print("未輸入關鍵字。")
        return

    results = search_videos_in_python(keyword)
    print_results(results, keyword=keyword)

    if results:
        export = input("是否將結果匯出到檔案? (y/n): ").lower()
        if export == "y":
            export_to_file(keyword, results)


def list_latest_videos():
    """列出資料庫中最新的影片"""
    limit = 20  # 預設列出 20 個
    try:
        limit_input = input(f"請輸入要列出的最新影片數量 (預設 {limit}): ").strip()
        if limit_input:
            limit = int(limit_input)
            if limit <= 0:
                limit = 20  # 輸入無效則使用預設值
    except ValueError:
        print("輸入無效，使用預設數量。")
        limit = 20

    results = get_latest_videos_from_db(limit)
    print_results(results, is_latest=True)

    if results:
        export = input("是否將結果匯出到檔案? (y/n): ").lower()
        if export == "y":
            export_to_file("latest", results, is_latest=True)


# --- 下載功能 (從原 main.py 整合) ---
def download_single_url():
    """提示用戶輸入單一 URL 並下載"""
    url = input("輸入 Jable 網址: ").strip()
    if url:
        download(url, is_batch=False)  # is_batch=False 表示需要詢問轉檔
    else:
        print("未輸入網址。")


def download_from_file():
    """使用檔案選擇對話框選擇檔案並批次下載，支持 latest_videos.txt 格式"""
    # 創建一個隱藏的 tkinter 根窗口
    root = tk.Tk()
    root.withdraw()  # 隱藏主窗口

    # 顯示檔案選擇對話框
    file_path = filedialog.askopenfilename(
        title="選擇包含網址列表的檔案",
        filetypes=[("文本檔案", "*.txt"), ("所有檔案", "*.*")],
        initialdir=os.getcwd(),  # 從當前目錄開始
    )

    # 關閉 tkinter 根窗口
    root.destroy()

    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            urls_from_file = []
            for i in range(len(lines)):
                if lines[i].strip().startswith("網址:"):
                    url = lines[i].strip().split("網址:")[1].strip()
                    urls_from_file.append(url)

            if not urls_from_file:
                print(f"錯誤：檔案 '{file_path}' 中未找到任何網址。")
            else:
                print(f"從檔案 '{file_path}' 讀取網址...")
                for url_from_file in urls_from_file:
                    print(f"開始下載 (批次): {url_from_file}")
                    download(url_from_file, is_batch=True)  # is_batch=True 自動轉檔
                print("檔案中的所有網址處理完畢。")
        except FileNotFoundError:
            print(f"錯誤：找不到檔案 '{file_path}'")
        except Exception as e:
            print(f"讀取或下載檔案 '{file_path}' 時發生錯誤: {e}")
    else:
        print("未選擇檔案，操作取消。")


# --- 主選單與主程式 ---
def show_main_menu():
    """顯示主選單並處理用戶選擇"""
    while True:
        print("\n========== Jable 工具箱 ==========")
        print("--- 下載 ---")
        print("1: 輸入單一 Jable 網址下載")
        print("2: 從檔案讀取網址列表批次下載")
        print("--- 爬取與管理 (需要 Selenium) ---")
        print("3: 爬取影片資訊並存入資料庫")
        print("4: 搜尋資料庫中的影片")
        print("5: 列出資料庫中最新收錄的影片")
        print("---------------------------------")
        print("0: 退出程式")
        print("=================================")

        choice = input("請輸入選項 (0-5): ").strip()

        if choice == "1":
            download_single_url()
        elif choice == "2":
            download_from_file()
        elif choice == "3":
            if SELENIUM_AVAILABLE:
                crawl_videos_by_type()
            else:
                print("錯誤：Selenium 組件未安裝或不可用，無法使用爬取功能。")
        elif choice == "4":
            search_videos()
        elif choice == "5":
            list_latest_videos()
        elif choice == "0":
            print("程式結束。")
            break
        else:
            print("無效的選項，請重新輸入。")


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    # 優先處理命令行參數
    if len(args.url) != 0:
        print(f"處理命令行參數 --url: {args.url}")
        download(args.url)
    elif args.file != "":
        print(f"處理命令行參數 --file: {args.file}")
        # 直接調用下載邏輯，不進入選單
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                urls_from_file = [line.strip() for line in f if line.strip()]
            if not urls_from_file:
                print(f"錯誤：檔案 '{args.file}' 是空的或只包含空白行。")
            else:
                print(f"從檔案 '{args.file}' 讀取網址...")
                for url_from_file in urls_from_file:
                    print(f"開始下載 (批次): {url_from_file}")
                    download(url_from_file, is_batch=True)
                print("檔案中的所有網址處理完畢。")
        except FileNotFoundError:
            print(f"錯誤：找不到檔案 '{args.file}'")
        except Exception as e:
            print(f"讀取或下載檔案 '{args.file}' 時發生錯誤: {e}")
    elif args.random == True:
        print("處理命令行參數 --random")
        url = av_recommand()
        if url:
            download(url)
        else:
            print("無法獲取隨機推薦網址。")
    elif args.all_urls != "":
        print(f"處理命令行參數 --all-urls: {args.all_urls}")
        urls = movieLinks(args.all_urls)
        if urls:
            for url in urls:
                download(url)  # 這裡可以考慮是否也用 is_batch=True
        else:
            print("無法從該頁面解析出影片連結。")
    else:
        # 如果沒有提供相關的命令行參數，則顯示互動選單
        show_main_menu()
