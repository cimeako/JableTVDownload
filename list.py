#!/usr/bin/env python
# -*- coding: utf-8 -*-

# --- 導入函式庫 ---
import time  # 用於時間延遲
import os  # 用於文件和路徑操作
import re  # 用於正則表達式 (提取 ID)
import traceback  # 用於打印詳細的錯誤堆棧信息
import pandas as pd  # 用於讀寫 Excel 文件
from tqdm import tqdm  # 用於顯示進度條
from bs4 import BeautifulSoup  # 用於解析 HTML

# --- Selenium 相關導入 (使用標準 Selenium) ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)

# --- 導入顯式等待相關模塊 ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 全局設定 ---
BASE_URL = "https://jable.tv"
LIST_URL_TEMPLATE = BASE_URL + "/latest-updates/{page}/"  # 目標：最新的更新列表頁
EXCEL_FILE = "jable_data.xlsx"  # 輸出的 Excel 文件名
EXPECTED_COLUMNS = [
    "網址編號",
    "主演",
    "影片名稱",
    "日期",
    "標籤",
    "中文字幕",
    "來源網址",
]  # Excel 列名
# 延遲設定 (秒)
DELAY_PAGE_LOAD = 8  # 頁面基礎加載等待時間 (秒)
DELAY_LIST_PAGE_NAV = 5  # 訪問不同列表頁之間的延遲 (秒)
DELAY_DETAIL_PAGE_NAV = 4  # 訪問不同詳細頁之間的延遲 (秒)
EXPLICIT_WAIT_TIMEOUT = 25  # 顯式等待的最長超時時間 (秒)

# --- Selenium WebDriver 選項設定 (採納您驗證有效的選項) ---
CHROME_OPTIONS = ChromeOptions()
# CHROME_OPTIONS.add_argument("--headless")             # 建議先註釋掉，方便調試時觀察瀏覽器
CHROME_OPTIONS.add_argument("--disable-gpu")
CHROME_OPTIONS.add_argument("--no-sandbox")
CHROME_OPTIONS.add_argument("--disable-dev-shm-usage")
# *** 關鍵選項：禁用 Blink 特性中的自動化控制標誌 ***
CHROME_OPTIONS.add_argument("--disable-blink-features=AutomationControlled")
# 設置 User-Agent
CHROME_OPTIONS.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)  # 來自您的有效代碼
# 其他可能有用的選項
CHROME_OPTIONS.add_experimental_option("excludeSwitches", ["enable-automation"])
CHROME_OPTIONS.add_experimental_option("useAutomationExtension", False)
CHROME_OPTIONS.add_argument("--window-size=1920,1080")

# --- 輔助函數 (用於 Excel 操作和 ID 提取) ---


def load_existing_ids(filename):
    """從 Excel 文件加載已存在的影片 ID 集合"""
    if os.path.exists(filename):
        try:
            df = pd.read_excel(filename, dtype={"網址編號": str})
            if "網址編號" in df.columns and not df["網址編號"].empty:
                return set(df["網址編號"].dropna().tolist())
        except Exception as e:
            print(f"警告：讀取 Excel 文件 '{filename}' 失敗: {e}")
    print(f"信息：未找到或無法讀取 '{filename}'，將從頭開始記錄。")
    return set()


def save_data(data_list, filename):
    """將爬取到的新數據保存或附加到 Excel 文件"""
    if not data_list:
        print("沒有新的數據需要保存。")
        return
    new_df = pd.DataFrame(data_list)
    for col in EXPECTED_COLUMNS:  # 確保所有列存在
        if col not in new_df.columns:
            new_df[col] = "N/A"
    new_df = new_df[EXPECTED_COLUMNS]  # 按預期順序排列
    for col in new_df.columns:  # 全部轉為字符串
        new_df[col] = new_df[col].astype(str)

    if os.path.exists(filename):
        try:
            existing_df = pd.read_excel(filename)
            for col in EXPECTED_COLUMNS:  # 確保舊數據也完整且為字符串
                if col in existing_df.columns:
                    existing_df[col] = existing_df[col].astype(str)
                else:
                    existing_df[col] = "N/A"
            existing_df = existing_df[EXPECTED_COLUMNS]
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.drop_duplicates(
                subset=["網址編號"], keep="last", inplace=True
            )  # 去重
            combined_df.reset_index(drop=True, inplace=True)
        except Exception as e:
            print(f"讀取或合併舊 Excel 文件 '{filename}' 出錯: {e}。將只保存新數據。")
            combined_df = new_df  # 出錯則只保留新數據
    else:
        combined_df = new_df  # 文件不存在，直接使用新數據

    if not combined_df.empty:
        try:
            combined_df.to_excel(
                filename, index=False, engine="openpyxl"
            )  # 保存到 Excel
            print(f"數據已成功保存到 {filename}")
        except Exception as e:
            print(f"保存 Excel 文件 '{filename}' 出錯: {e}")
            traceback.print_exc()


def extract_video_id(url):
    """從影片 URL 中提取番號/ID"""
    if not url:
        return None
    match = re.search(r"/videos/([^/]+)/?$", url)
    if match:
        return match.group(1)
    return None


# --- 爬取影片詳細頁信息的函數 ---
def get_video_details(video_url, driver):
    """使用 Selenium driver 訪問並解析影片詳細頁"""
    try:
        # print(f"  正在導航到詳細頁: {video_url}") # 調試信息
        driver.get(video_url)

        # --- 使用顯式等待，等待關鍵信息（如標題 H4）加載完成 ---
        try:
            WebDriverWait(driver, EXPLICIT_WAIT_TIMEOUT).until(
                # 等待 h4 標題元素可見
                EC.visibility_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "section.video-info div.info-header div.header-left h4",
                    )
                )
            )
            # print(f"  詳細頁標題元素已加載 @ {video_url}") # 調試信息
        except TimeoutException:
            # 如果超時，檢查是否是 Cloudflare 或錯誤頁面
            page_title = driver.title
            print(f"警告：等待詳細頁標題元素超時 @ {video_url} (標題: {page_title})。")
            if (
                "Just a moment" in page_title
                or "Checking your browser" in page_title
                or "403 Forbidden" in page_title
            ):
                print("錯誤：詳細頁面是 Cloudflare 或錯誤頁面。跳過。")
                return None
            # 即使超時，仍嘗試解析頁面，可能部分信息已加載
            print("將嘗試繼續解析可能已加載的部分內容...")

        # 短暫固定等待，確保 JS 渲染
        time.sleep(2)

        # --- 獲取頁面源碼並解析 ---
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        # (解析邏輯與之前版本相同)
        details = {
            "網址編號": extract_video_id(video_url) or "提取失敗",
            "主演": "N/A",
            "影片名稱": "N/A",
            "日期": "N/A",
            "標籤": "N/A",
            "中文字幕": "否",
            "來源網址": video_url,
        }
        info_header = soup.select_one(
            "section.video-info div.info-header div.header-left"
        )
        page_title = driver.title  # 更新標題以備用
        if info_header:
            actors = []
            actor_imgs = info_header.select(
                "div.models img.avatar[data-original-title]"
            )
            for img in actor_imgs:
                if "data-original-title" in img.attrs and img["data-original-title"]:
                    actors.append(img["data-original-title"].strip())
            if not actors:
                actor_links = info_header.select("div.models a.model")
                for link in actor_links:
                    if link.text.strip():
                        actors.append(link.text.strip())
            if actors:
                details["主演"] = ", ".join(list(set(actors)))
            title_h4 = info_header.select_one("h4")
            if title_h4:
                details["影片名稱"] = title_h4.text.strip()
            date_span = info_header.select_one(
                'h6 svg[xlink\\:href="#icon-clock"] + span.mr-3'
            )
            if date_span:
                details["日期"] = date_span.text.strip()
            else:
                date_spans = info_header.select("h6 span.mr-3")
                if date_spans:
                    details["日期"] = date_spans[0].text.strip()
        else:
            details["影片名稱"] = page_title.replace(
                " - Jable.TV｜高畫質免費A片", ""
            ).strip()

        tags_list = []
        has_chinese_subtitle_tag = False
        tags_container = soup.select_one("h5.tags.h6-md")
        if tags_container:
            tags_elements = tags_container.select('a.cat, a[href*="/tags/"]')
            for tag_a in tags_elements:
                tag_text = tag_a.text.strip()
                if tag_text:
                    tags_list.append(tag_text)
                    if "中文字幕" in tag_text:
                        has_chinese_subtitle_tag = True
        subtitle_header_text = ""
        subtitle_header = soup.select_one("div.info-header div.header-right h6")
        if subtitle_header:
            subtitle_header_text = subtitle_header.text.strip()
        if has_chinese_subtitle_tag or "中文字幕" in subtitle_header_text:
            details["中文字幕"] = "是"
            if "中文字幕" not in tags_list and "中文字幕" in subtitle_header_text:
                tags_list.append("中文字幕(頁眉)")
        if tags_list:
            details["標籤"] = ", ".join(list(set(tags_list)))
        return details

    except TimeoutException:
        print(f"\n錯誤：加載詳細頁 {video_url} 超時。")
        return None
    except NoSuchElementException as e:
        print(f"\n錯誤：在詳細頁 {video_url} 找不到元素: {e}")
        return None
    except WebDriverException as e:
        print(f"\n錯誤：WebDriver 操作詳細頁失敗 ({video_url}): {e}")
        return None
    except Exception as e:
        print(f"\n錯誤：解析詳細頁 {video_url} 時發生未預期錯誤: {e}")
        traceback.print_exc()
        return None


# --- 主程序入口 ---
if __name__ == "__main__":
    print("--- Jable.tv 最新影片爬蟲 (Selenium + 整合有效選項 + 顯式等待) ---")
    print(f"數據將保存到: {EXCEL_FILE}")
    existing_ids = load_existing_ids(EXCEL_FILE)  # 加載已存在的 ID
    print(f"已加載 {len(existing_ids)} 個已存在的影片 ID。")
    max_pages = 0
    while True:  # 獲取用戶輸入
        try:
            pages_input = input(f"請輸入要爬取的最新影片頁數 (例如 5，輸入 0 退出): ")
            if not pages_input:
                continue
            max_pages = int(pages_input)
            if max_pages == 0:
                exit()
            elif max_pages > 0:
                break
            else:
                print("請輸入一個正整數或 0。")
        except ValueError:
            print("輸入無效，請輸入一個數字。")
        except EOFError:
            print("\n檢測到輸入終止符。程序退出。")
            exit()

    # --- 初始化 Selenium WebDriver ---
    driver = None
    try:
        print("\n正在初始化 WebDriver...")
        service = ChromeService(ChromeDriverManager().install())
        # 使用包含有效選項的 CHROME_OPTIONS
        driver = webdriver.Chrome(service=service, options=CHROME_OPTIONS)
        print("WebDriver 初始化成功。")
        driver.set_page_load_timeout(60)  # 設置頁面加載超時

        # 可選：先訪問主頁
        print(f"嘗試訪問主頁: {BASE_URL}")
        driver.get(BASE_URL)
        time.sleep(5)  # 等待主頁基礎加載
        print(f"當前頁面標題: {driver.title}")
        if (
            "403 Forbidden" in driver.title
            or "Access denied" in driver.page_source
            or "Just a moment" in driver.title
        ):
            print("錯誤：訪問主頁時顯示 403/Access Denied/Cloudflare。程序將終止。")
            if driver:
                driver.quit()
            exit()
    except WebDriverException as e:
        print(f"WebDriver 初始化失敗: {e}")
        exit()
    except Exception as e:
        print(f"初始化過程中發生未知錯誤: {e}")
        traceback.print_exc()
    if driver:
        driver.quit()
        exit()

    # --- 開始爬取循環 ---
    new_data = []
    processed_ids_current_run = set()
    print(f"\n開始爬取 Jable.tv 最新的 {max_pages} 頁影片...")
    print("-" * 30)

    try:  # 主循環 try...finally 確保 driver.quit() 被調用
        for page_num in tqdm(
            range(1, max_pages + 1), desc="總體進度 (頁數)", unit="頁"
        ):
            list_url = LIST_URL_TEMPLATE.format(page=page_num)  # 構建列表頁 URL
            # print(f"\n[第 {page_num}/{max_pages} 頁] 正在導航到列表頁: {list_url}") # 調試

            try:  # 處理單個列表頁的 try...except
                driver.get(list_url)  # 訪問列表頁

                # --- 使用顯式等待代替固定 sleep，等待列表內容加載 ---
                print(
                    f"  等待列表頁 {page_num} 內容加載 (最長 {EXPLICIT_WAIT_TIMEOUT} 秒)..."
                )
                try:
                    # 等待第一個代表視頻的連結元素出現
                    WebDriverWait(driver, EXPLICIT_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.img-box.cover-md > a")
                        )
                    )
                    print(f"  列表頁 {page_num} 內容已加載。")
                    time.sleep(2)  # 短暫等待確保渲染
                except TimeoutException:
                    # 等待超時
                    page_title = driver.title
                    print(
                        f"\n錯誤：等待列表頁 {page_num} ({list_url}) 的視頻元素超時 (標題: {page_title})。"
                    )
                    if (
                        "Just a moment" in page_title
                        or "Checking your browser" in page_title
                        or "403 Forbidden" in page_title
                    ):
                        print("錯誤：頁面是 Cloudflare 或錯誤頁面。停止爬取。")
                        break  # 停止外層循環
                    else:
                        print("頁面結構可能已更改，或異步加載失敗。跳過此頁。")
                        continue  # 繼續下一頁

                # --- 獲取頁面源碼並解析 ---
                list_page_source = driver.page_source
                list_soup = BeautifulSoup(list_page_source, "html.parser")
                video_links_elements = list_soup.select(
                    "div.img-box.cover-md > a"
                )  # 獲取所有視頻連結元素

                # --- 檢查是否找到連結 ---
                if not video_links_elements:
                    no_videos_msg = list_soup.find(
                        text=re.compile("沒有找到任何影片|No videos found")
                    )
                    if no_videos_msg:
                        print(
                            f"\n信息：第 {page_num} 頁 ({list_url}) 沒有影片內容。停止。"
                        )
                        break
                    print(
                        f"\n警告：第 {page_num} 頁 ({list_url}) 未找到影片連結元素。跳過。"
                    )
                    continue

                page_new_videos_count = 0  # 本頁新增計數
                # --- 遍歷本頁找到的視頻連結 ---
                for link_element in tqdm(
                    video_links_elements,
                    desc=f"處理第 {page_num} 頁",
                    leave=False,
                    unit="影片",
                ):
                    video_url_href = link_element.get("href")
                    if not video_url_href:
                        continue

                    # 構建完整 URL
                    if video_url_href.startswith("http"):
                        video_full_url = video_url_href
                    elif video_url_href.startswith("/videos/"):
                        video_full_url = BASE_URL + video_url_href
                    else:
                        continue

                    # 提取 ID
                    video_id = extract_video_id(video_full_url)
                    if not video_id:
                        continue

                    # 檢查是否已存在
                    if (
                        video_id in existing_ids
                        or video_id in processed_ids_current_run
                    ):
                        continue

                    # 爬取詳細信息
                    details = get_video_details(video_full_url, driver)
                    if details:  # 如果成功返回字典
                        new_data.append(details)
                        processed_ids_current_run.add(details["網址編號"])
                        page_new_videos_count += 1
                    else:
                        print(
                            f"  未能獲取影片詳細信息: {video_full_url}"
                        )  # 函數內部已打印錯誤

                    time.sleep(DELAY_DETAIL_PAGE_NAV)  # 詳細頁之間延遲

                # 打印本頁總結
                if video_links_elements:
                    print(
                        f"\n第 {page_num} 頁處理完畢：共找到 {len(video_links_elements)} 個連結，新增 {page_new_videos_count} 筆新資料。"
                    )
                    if page_new_videos_count == 0 and len(video_links_elements) > 0:
                        print(
                            f"  提示：第 {page_num} 頁的所有影片似乎都已存在於記錄中。"
                        )

            # --- 列表頁級別的異常處理 ---
            except TimeoutException:
                print(f"\n錯誤：加載列表頁 {list_url} 總體超時。跳過此頁。")
                time.sleep(5)
            except WebDriverException as e:
                print(f"\n錯誤：WebDriver 操作列表頁 {list_url} 失敗: {e}")
                time.sleep(5)
                continue  # 嘗試繼續下一頁
            except Exception as e:
                print(f"\n錯誤：處理列表頁 {list_url} 時發生未預期錯誤: {e}")
                traceback.print_exc()
                time.sleep(DELAY_LIST_PAGE_NAV)

            time.sleep(DELAY_LIST_PAGE_NAV)  # 列表頁之間延遲

    finally:  # --- 確保關閉瀏覽器 ---
        if driver:
            print("\n正在關閉 WebDriver...")
            try:
                driver.quit()
                print("WebDriver 已關閉。")
            except OSError as e:
                print(f"關閉 WebDriver 時發生 OSError (可能正常): {e}")
            except Exception as e:
                print(f"關閉 WebDriver 時發生未知錯誤: {e}")
                traceback.print_exc()

    # --- 保存最終結果 ---
    print("-" * 30)
    print("\n爬取流程完成。")
    if new_data:
        print(f"本次運行共抓取到 {len(new_data)} 筆新資料。")
        print("正在將數據保存到 Excel 文件...")
        save_data(new_data, EXCEL_FILE)
    else:
        print("本次運行沒有抓取到任何新的影片資料。")
    print("\n程序執行完畢。")
