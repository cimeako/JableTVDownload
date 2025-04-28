#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import os
import re
import sqlite3
import sys
import datetime
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Selenium 相關導入
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 資料庫設定
DB_PATH = "D:\\jable\\spider_for_jable.tv\\test.db"

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


# --- 資料庫相關函數 ---
def setup_database():
    """設置資料庫，如果不存在則創建"""
    # 檢查資料庫目錄是否存在，如果不存在則創建
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"已創建目錄: {db_dir}")

    # 連接資料庫（如果不存在會自動創建）
    conn = sqlite3.connect(DB_PATH)
    print(f"已連接到資料庫: {DB_PATH}")

    # 啟用外鍵約束
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 創建資料表（如果不存在）
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
    print("資料表結構:")
    for column in columns:
        print(column)

    # 檢查是否需要添加 crawl_date 欄位
    column_names = [column[1] for column in columns]
    if "crawl_date" not in column_names:
        print("添加 crawl_date 欄位到資料表")
        cursor.execute("ALTER TABLE av_db ADD COLUMN crawl_date TEXT")
        conn.commit()

    # 檢查是否需要添加 crawl_type 欄位
    if "crawl_type" not in column_names:
        print("添加 crawl_type 欄位到資料表")
        cursor.execute("ALTER TABLE av_db ADD COLUMN crawl_type TEXT")
        conn.commit()

    # 檢查是否需要添加 crawl_value 欄位
    if "crawl_value" not in column_names:
        print("添加 crawl_value 欄位到資料表")
        cursor.execute("ALTER TABLE av_db ADD COLUMN crawl_value TEXT")
        conn.commit()


def search_videos_in_python(keyword):
    """在 Python 中進行過濾搜尋"""
    try:
        # 連接資料庫
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 獲取所有記錄
        cursor.execute("SELECT fanhao, url, title, crawl_date FROM av_db")
        all_records = cursor.fetchall()

        # 關閉資料庫連接
        cursor.close()
        conn.close()

        # 在 Python 中進行過濾
        keyword_lower = keyword.lower()  # 轉為小寫以進行不區分大小寫的搜尋
        results = []

        for record in all_records:
            fanhao, url, title, crawl_date = record
            # 檢查標題或番號是否包含關鍵字
            if (title and keyword_lower in title.lower()) or (
                fanhao and keyword_lower in fanhao.lower()
            ):
                results.append((fanhao, url, title, crawl_date))

        return results
    except Exception as e:
        print(f"搜尋時發生錯誤: {e}")
        return []


def get_latest_videos(limit=20):
    """獲取最新的影片（按照收錄日期排序）"""
    try:
        # 連接資料庫
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 獲取最新的記錄
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

        # 關閉資料庫連接
        cursor.close()
        conn.close()

        return latest_records
    except Exception as e:
        print(f"獲取最新影片時發生錯誤: {e}")
        return []


def export_to_file(keyword, results, is_latest=False):
    """將搜尋結果匯出到檔案"""
    try:
        # 創建輸出檔案名稱
        if is_latest:
            filename = "latest_videos.txt"
            title = f"最新收錄的 {len(results)} 部影片"
        else:
            filename = f"{keyword}.txt"
            title = f"關鍵字 '{keyword}' 的搜尋結果"

        # 寫入搜尋結果
        with open(filename, "w", encoding="utf-8") as f:
            # 寫入標題行
            f.write(f"{title}:\n")
            f.write("=" * 80 + "\n\n")

            # 寫入每個搜尋結果
            for i, (fanhao, url, title, crawl_date) in enumerate(results, 1):
                f.write(f"{i}. {title}\n")
                f.write(f"   番號: {fanhao}\n")
                f.write(f"   網址: {url}\n")
                if crawl_date:
                    f.write(f"   收錄日期: {crawl_date}\n")
                f.write("\n")

            # 寫入統計資訊
            f.write("-" * 80 + "\n")
            if is_latest:
                f.write(f"共列出 {len(results)} 個最新收錄的影片\n")
            else:
                f.write(f"共找到 {len(results)} 個符合關鍵字 '{keyword}' 的影片\n")

            # 添加方便複製的 URL 列表
            f.write("\n\n方便複製的 URL 列表:\n")
            for fanhao, url, title, _ in results:
                f.write(f"{url}\n")

        print(f"結果已匯出到檔案: {filename}")
        return True
    except Exception as e:
        print(f"匯出檔案時發生錯誤: {e}")
        return False


def print_results(results, is_latest=False):
    """在控制台顯示結果"""
    if not results:
        if is_latest:
            print("沒有找到任何影片")
        else:
            print("找不到符合的影片")
        return

    if is_latest:
        print(f"\n最新收錄的 {len(results)} 部影片:")
    else:
        print(f"\n找到 {len(results)} 個符合的影片:")

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
    """設置 Selenium 並使用代理"""
    options = Options()

    # 添加代理設定
    proxy = ""
    options.add_argument(f"--proxy-server={proxy}")

    # 添加其他設定
    options.add_argument("--headless")  # 無頭模式，不顯示瀏覽器窗口
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # 創建 WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 設置頁面加載超時
    driver.set_page_load_timeout(30)

    return driver


def get_page_with_selenium(driver, url):
    """使用 Selenium 獲取頁面內容"""
    try:
        print(f"正在訪問頁面: {url}")
        driver.get(url)

        # 等待頁面加載
        time.sleep(5)

        # 獲取頁面源碼
        page_source = driver.page_source
        print("頁面獲取成功")

        # 保存 HTML 以便分析
        with open(f"jable_page_{time.time()}.html", "w", encoding="utf-8") as f:
            f.write(page_source)

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

    # 針對 AJAX 響應的特殊處理
    # 檢查是否是 JSON 格式
    if html_content.strip().startswith("{") and html_content.strip().endswith("}"):
        try:
            # 嘗試解析 JSON
            json_data = json.loads(html_content)
            if "html" in json_data:
                # 使用 JSON 中的 HTML 內容
                soup = BeautifulSoup(json_data["html"], "html.parser")
        except:
            pass

    # 嘗試多種可能的選擇器
    video_containers = (
        soup.select("div.video-img-box")
        or soup.select("div.col-6.col-sm-4.col-lg-3")
        or soup.select("div.thumb-overlay")
    )

    print(f"找到 {len(video_containers)} 個視頻容器")

    for container in video_containers:
        try:
            # 嘗試找到標題和鏈接
            title_element = container.select_one("h6.title a") or container.select_one(
                "a.title"
            )

            if title_element:
                title = title_element.text.strip()
                url = title_element.get("href")

                # 從 URL 中提取番號
                path_parts = urlparse(url).path.split("/")
                fanhao = path_parts[2] if len(path_parts) > 2 else ""

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

    # 獲取當前日期，格式為 YYYY-MM-DD
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    for video in videos:
        fanhao = video["f"]
        if not fanhao or fanhao in existing_fanhaos:
            print(f"跳過已存在的番號: {fanhao}")
            found_existing = True
            continue

        try:
            cursor.execute(
                "INSERT INTO av_db (fanhao, url, title, crawl_date, crawl_type, crawl_value) VALUES (?, ?, ?, ?, ?, ?)",
                (fanhao, video["u"], video["t"], current_date, crawl_type, crawl_value),
            )
            existing_fanhaos.add(fanhao)  # 更新已存在番號集合
            new_videos_count += 1
            print(f"已保存: {fanhao} - {video['t']} - 爬取日期: {current_date}")
        except sqlite3.IntegrityError:
            # 處理唯一性約束衝突
            print(f"番號已存在 (衝突): {fanhao}")
            found_existing = True
        except Exception as e:
            print(f"保存視頻時出錯: {e}")

    conn.commit()
    print(f"本頁新增了 {new_videos_count} 個新影片")
    return found_existing


def crawl_videos_by_type():
    """根據用戶選擇的類型爬取視頻"""
    try:
        # 設置資料庫
        conn, cursor = setup_database()

        # 檢查資料表結構
        check_db_structure(conn, cursor)

        # 獲取已存在的番號
        existing_fanhaos = get_existing_fanhaos(cursor)
        print(f"資料庫中已有 {len(existing_fanhaos)} 個影片")

        # 選擇爬取類型
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

        # 根據選擇設置爬取參數
        url_template = ""
        crawl_type = ""
        crawl_value = ""

        if crawl_type_choice == "1":
            # 最新影片
            url_template = URL_TEMPLATES["latest"]
            crawl_type = "latest"
            crawl_value = ""

        elif crawl_type_choice == "2":
            # 特定女優
            crawl_type = "actress"
            print(f"\n預設女優: {DEFAULT_VALUES['actress']}")
            crawl_value = (
                input(f"請輸入女優ID (直接按Enter使用預設值): ").strip()
                or DEFAULT_VALUES["actress"]
            )
            url_template = URL_TEMPLATES["actress"].format(crawl_value)

        elif crawl_type_choice == "3":
            # 特定類別
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
            # 特定標籤
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

        # 獲取爬取頁數
        max_pages = 0
        while True:
            try:
                pages_input = input(f"請輸入要爬取的頁數 (例如 5，輸入 0 返回): ")
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

        # 設置 Selenium
        driver = setup_selenium_with_proxy()

        try:
            for page in range(1, max_pages + 1):
                page_url = f"{url_template}{page:02d}"  # 使用兩位數格式
                print(f"正在處理第 {page}/{max_pages} 頁")

                html_content = get_page_with_selenium(driver, page_url)

                if html_content:
                    videos = parse_videos(html_content)

                    if videos:
                        # 保存視頻到資料庫，並檢查是否發現已存在的影片
                        found_existing = save_to_database(
                            conn,
                            cursor,
                            videos,
                            existing_fanhaos,
                            crawl_type,
                            crawl_value,
                        )
                        print(f"第 {page} 頁處理完成，找到 {len(videos)} 個視頻")

                        # 如果發現已存在的影片，詢問是否繼續
                        if found_existing and page < max_pages:
                            continue_choice = (
                                input("發現已存在的影片，是否繼續爬取下一頁? (y/n): ")
                                .strip()
                                .lower()
                            )
                            if continue_choice != "y":
                                print("停止爬取")
                                break
                    else:
                        print(f"第 {page} 頁沒有找到視頻")
                        # 如果沒有找到視頻，可能已經到達最後一頁
                        continue_choice = (
                            input("沒有找到視頻，是否繼續爬取下一頁? (y/n): ")
                            .strip()
                            .lower()
                        )
                        if continue_choice != "y":
                            print("停止爬取")
                            break

                # 等待一段時間再訪問下一頁
                delay = 5
                print(f"等待 {delay} 秒...")
                time.sleep(delay)

        except KeyboardInterrupt:
            print("程式被使用者中斷")
        except Exception as e:
            print(f"爬取過程中發生錯誤: {e}")
        finally:
            # 關閉 Selenium
            if driver:
                driver.quit()

            # 檢查結果並顯示最新的10條記錄
            print("\n最新加入的10筆資料:")
            try:
                cursor.execute(
                    "SELECT id, fanhao, title, crawl_date, crawl_type, crawl_value FROM av_db ORDER BY id DESC LIMIT 10"
                )
                latest_records = cursor.fetchall()
                for record in latest_records:
                    print(
                        f"ID: {record[0]}, 番號: {record[1]}, 標題: {record[2]}, "
                        f"爬取日期: {record[3]}, 類型: {record[4]}, 值: {record[5]}"
                    )
            except Exception as e:
                print(f"查詢最新記錄時出錯: {e}")

            # 顯示總數
            cursor.execute("SELECT COUNT(*) FROM av_db")
            count = cursor.fetchone()[0]
            print(f"\n資料庫中總共有 {count} 個視頻")

    except Exception as e:
        print(f"程式執行時發生錯誤: {e}")
    finally:
        # 確保關閉資料庫連接
        if "conn" in locals() and conn:
            cursor.close()
            conn.close()
            print("資料庫連接已關閉")

        print("爬蟲執行完畢")


def search_videos():
    """搜尋影片功能"""
    # 檢查資料庫是否存在
    if not os.path.exists(DB_PATH):
        print(f"錯誤: 找不到資料庫檔案 {DB_PATH}")
        return

    # 獲取搜尋關鍵字
    keyword = input("請輸入搜尋關鍵字: ").strip()

    if not keyword:
        print("錯誤: 關鍵字不能為空")
        return

    print(f"正在搜尋關鍵字: {keyword}")

    # 使用 Python 進行搜尋
    results = search_videos_in_python(keyword)

    # 顯示搜尋結果
    print_results(results)

    if results:
        # 匯出搜尋結果
        export_to_file(keyword, results)
    else:
        # 顯示一些標題樣本，幫助確認關鍵字是否正確
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM av_db LIMIT 10")
        sample_titles = cursor.fetchall()
        print("\n資料庫中的一些標題樣本:")
        for title in sample_titles:
            print(f"- {title[0]}")
        cursor.close()
        conn.close()


def list_latest_videos():
    """列出最新收錄的影片功能"""
    # 檢查資料庫是否存在
    if not os.path.exists(DB_PATH):
        print(f"錯誤: 找不到資料庫檔案 {DB_PATH}")
        return

    print("正在獲取最新收錄的影片...")
    latest_videos = get_latest_videos(20)

    # 顯示結果
    print_results(latest_videos, is_latest=True)

    if latest_videos:
        # 匯出結果
        export_to_file("latest", latest_videos, is_latest=True)


def show_menu():
    """顯示主選單"""
    print("\n" + "=" * 50)
    print("Jable 影片管理系統")
    print("=" * 50)
    print("1. 爬取影片 (多種類型)")
    print("2. 關鍵字搜尋")
    print("3. 列出最新收錄的20部影片")
    print("0. 退出")
    print("-" * 50)

    choice = input("請選擇功能 (0-3): ").strip()
    return choice


def main():
    """主函數"""
    while True:
        choice = show_menu()

        if choice == "0":
            print("程式已退出")
            break

        elif choice == "1":
            # 爬取影片 (多種類型)
            crawl_videos_by_type()

        elif choice == "2":
            # 關鍵字搜尋
            search_videos()

        elif choice == "3":
            # 列出最新收錄的影片
            list_latest_videos()

        else:
            print("無效的選擇，請重新輸入")


if __name__ == "__main__":
    main()
