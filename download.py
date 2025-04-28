import requests
import os
import re
import urllib.request
import m3u8
from Crypto.Cipher import AES
from config import headers
from crawler import prepareCrawl
from merge import mergeMp4
from delete import deleteM3u8, deleteMp4
from cover import getCover
from encode import ffmpegEncode
from args import *
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def download(url, is_batch=False):
    encode = 0  # 不轉檔
    if is_batch:
        print("批次處理模式：自動選擇轉檔方案 1")
        encode = 1  # 批次模式下，預設使用方案1轉檔
    else:
        # 維持原有的詢問邏輯
        action = input("要轉檔嗎?[y/n]")
        if action.lower() == "y":
            action = input(
                "選擇轉檔方案[1:僅轉換格式(默認,推薦) 2:NVIDIA GPU 轉檔 3:CPU 轉檔]"
            )
            if action == "2":
                encode = 2  # GPU轉檔
            elif action == "3":
                encode = 3  # CPU轉檔
            else:
                encode = 1  # 快速無損轉檔

    print("正在下載影片: " + url)

    # --- 修正路徑問題 ---
    # 獲取腳本啟動時的基礎目錄 (通常是 JableTVDownload)
    # 使用 __file__ 獲取當前腳本的絕對路徑，再取其目錄，確保是固定的基礎路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 如果希望下載目錄固定在 JableTVDownload，可以直接指定
    # base_download_dir = "d:/jable/JableTVDownload" # 或者使用 script_dir 如果腳本就在 JableTVDownload
    base_download_dir = script_dir  # 假設 download.py 在 JableTVDownload 目錄下

    # 從 URL 取得番號作為資料夾名
    urlSplit = url.split("/")
    dirName = urlSplit[-2]

    # 計算絕對目標資料夾路徑
    folderPath = os.path.join(base_download_dir, dirName)

    # 檢查目標影片檔案是否已存在 (使用絕對路徑檢查)
    target_mp4_path = os.path.join(folderPath, f"{dirName}.mp4")
    if os.path.exists(target_mp4_path):
        print(f"影片檔案 {target_mp4_path} 已存在, 跳過...")
        return

    # 建立目標資料夾 (如果不存在，使用絕對路徑建立)
    if not os.path.exists(folderPath):
        os.makedirs(folderPath)
    # --- 修正結束 ---

    # 配置Selenium參數
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36"
    )
    dr = webdriver.Chrome(options=options)
    dr.get(url)
    result = re.search("https://.+m3u8", dr.page_source)
    print(f"result: {result}")
    m3u8url = result[0]
    print(f"m3u8url: {m3u8url}")

    # 得到 m3u8 網址
    m3u8urlList = m3u8url.split("/")
    m3u8urlList.pop(-1)
    downloadurl = "/".join(m3u8urlList)

    # 儲存 m3u8 file 至資料夾
    m3u8file = os.path.join(folderPath, dirName + ".m3u8")
    urllib.request.urlretrieve(m3u8url, m3u8file)

    # 得到 m3u8 file裡的 URI和 IV
    m3u8obj = m3u8.load(m3u8file)
    m3u8uri = ""
    m3u8iv = ""

    for key in m3u8obj.keys:
        if key:
            m3u8uri = key.uri
            m3u8iv = key.iv

    # 儲存 ts網址 in tsList
    tsList = []
    for seg in m3u8obj.segments:
        tsUrl = downloadurl + "/" + seg.uri
        tsList.append(tsUrl)

    # 有加密
    if m3u8uri:
        m3u8keyurl = downloadurl + "/" + m3u8uri  # 得到 key 的網址
        # 得到 key的內容
        response = requests.get(m3u8keyurl, headers=headers, timeout=10)
        contentKey = response.content

        vt = m3u8iv.replace("0x", "")[:16].encode()  # IV取前16位

        ci = AES.new(contentKey, AES.MODE_CBC, vt)  # 建構解碼器
    else:
        ci = ""

    # 刪除m3u8 file
    deleteM3u8(folderPath)

    # 開始爬蟲並下載mp4片段至資料夾
    prepareCrawl(ci, folderPath, tsList)

    # 合成mp4
    mergeMp4(folderPath, tsList)

    # 刪除子mp4
    deleteMp4(folderPath)

    # 取得封面
    getCover(html_file=dr.page_source, folder_path=folderPath)

    # 轉檔
    ffmpegEncode(folderPath, dirName, encode)
