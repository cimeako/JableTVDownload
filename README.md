# JableTVDownload

## 概述

JableTVDownload 是一個用於下載 Jable TV 影片的工具，旨在解決在線觀看時可能遇到的緩衝問題。它允許用戶將影片下載到本地計算機，並提供了影片搜索、獲取最新影片列表以及自動轉檔等功能。

## 主要功能

*   **影片下載**：輸入 Jable TV 影片網址即可下載。
*   **批量下載**：支持輸入演員、分類或標籤頁面鏈接，下載相關的所有影片。
*   **最新影片**：快速獲取並列出 Jable TV 上最新更新的影片。
*   **影片搜索**：根據關鍵字在已爬取的數據庫中搜索影片。
*   **自動轉檔**：可選使用 FFmpeg 將下載的影片片段合併並轉檔為完整的 MP4 文件。
*   **封面抓取**：下載完成後自動抓取影片封面。
*   **命令行支持**：支持通過命令行參數指定下載網址或執行特定操作（如隨機下載熱門影片）。

## 環境要求

*   **Python**: 3.6 或更高版本。
*   **FFmpeg**: （可選，但強烈建議安裝）用於影片合併和轉檔。請確保已將 FFmpeg 添加到系統的環境變量中。
*   **Chrome/Chromium**: 需要安裝 Chrome 瀏覽器或 Chromium。
*   **ChromeDriver**: 需要與您的 Chrome/Chromium 版本匹配的 ChromeDriver。

## 安裝步驟 (Windows 懶人包)

1.  **安裝 FFmpeg**: 
    *   訪問 [FFmpeg 官網](https://www.ffmpeg.org/download.html) 下載適合您系統的版本。
    *   解壓下載的文件。
    *   將解壓後文件夾內的 `bin` 目錄路徑添加到系統的環境變量 `Path` 中。
    *   打開新的命令提示符窗口，輸入 `ffmpeg -version`，如果顯示版本信息，則表示安裝成功。
    ![FFmpeg 安裝成功示例](img/ffmpeg.png)

2.  **執行初始化腳本**: 
    *   雙擊運行 `INIT.bat` 文件。
    *   此腳本會自動：
        *   創建 Python 虛擬環境 (`jable` 文件夾)。
        *   激活虛擬環境。
        *   根據 `requirements.txt` 安裝所有必要的 Python 庫。
        *   檢查並下載與您 Chrome 版本匹配的 `chromedriver.exe`。
        *   檢查 FFmpeg 是否已正確安裝並添加到環境變量。
    *   看到提示「FFmpeg已安裝，你可以執行RUN.bat了」即表示環境設置完成。

## 使用方法

1.  **運行工具**: 雙擊運行 `RUN.bat` 文件。
2.  **輸入網址或選擇操作**: 
    *   **下載單個影片**: 直接粘貼 Jable TV 影片的網址 (例如: `https://jable.tv/videos/ipx-486/`)。
    *   **批量下載 (演員/分類/標籤)**: 粘貼演員、分類或標籤頁面的網址(可從搜索影片或獲取最新影片導出的TXT文件讀取)。
    *   **搜索影片**: 輸入 `s` 或 `search`，然後輸入關鍵字進行搜索。
    *   **獲取最新影片**: 輸入 `l` 或 `latest` 查看最新收錄的影片。
    *   **退出**: 輸入 `q` 或 `quit`。
    ![輸入網址示例](img/download2.PNG)
3.  **選擇是否轉檔**: 下載完成後，會提示是否進行轉檔。
    *   輸入 `y` 進行轉檔，`n` 跳過。
    *   如果選擇轉檔，會進一步詢問是否使用 GPU 加速 (需要兼容的 Nvidia 顯卡和驅動)。
    ![下載與轉檔選項](img/download.PNG)
4.  **等待完成**: 等待下載和（如果選擇了）轉檔過程完成。
    ![轉檔中](img/encoding.png)
    ![轉檔完成](img/encoded.png)
5.  **查看結果**: 下載的影片（和封面）會保存在以影片番號命名的文件夾中。
    ![完成示例](img/demo2.png)

## 命令行參數

可以使用 `python main.py -h` 查看所有可用的命令行參數。

```bash
usage: main.py [-h] [--url URL] [--random RANDOM] [--latest LATEST] [--search SEARCH]

Jable TV Downloader

optional arguments:
  -h, --help       show this help message and exit
  --url URL        直接指定要下載的 Jable TV 影片 URL
  --random RANDOM  下載隨機熱門影片 (True/False)
  --latest LATEST  獲取最新的影片列表 (指定數量，例如 10)
  --search SEARCH  根據關鍵字搜索資料庫中的影片
```

**示例:**

*   下載指定 URL 的影片: `python main.py --url https://jable.tv/videos/ipx-486/`
*   下載隨機熱門影片: `python main.py --random True`
*   獲取最新的 20 部影片: `python main.py --latest 20`
*   搜索包含關鍵字 "OL" 的影片: `python main.py --search OL`

## 文件說明

*   `main.py`: 主程序入口。
*   `download.py`: 處理影片下載邏輯。
*   `encode.py`: 處理影片轉檔邏輯。
*   `getList.py`: 處理獲取影片列表和搜索邏輯。
*   `cover.py`: 處理封面下載邏輯。
*   `config.py`: 包含請求頭等配置。
*   `args.py`: 處理命令行參數。
*   `requirements.txt`: Python 依賴庫列表。
*   `INIT.bat`: Windows 初始化腳本。
*   `RUN.bat`: Windows 運行腳本。
*   `getchromedriver.py`: 自動下載 ChromeDriver 的腳本。
*   `test.db`: SQLite 資料庫，存儲已爬取的影片信息。
*   `latest_videos.txt`: 運行獲取最新影片功能時生成的列表文件。
*   `[關鍵字].txt`: 運行搜索功能時生成的列表文件。
*   `[番號]/`: 每個下載的影片會存放在以其番號命名的文件夾內。
*   `img/`: 存放 README 文檔中使用的圖片。
*   `jable/`: Python 虛擬環境文件夾。

## 注意事項

*   **網絡問題**: 請確保網絡連接穩定。
*   **ChromeDriver 版本**: `INIT.bat` 會嘗試自動下載匹配的 ChromeDriver，但如果失敗或 Chrome 更新後，可能需要手動下載並替換 `chromedriver.exe` 文件。請從 [ChromeDriver 官網](https://chromedriver.chromium.org/downloads) 下載。
*   **FFmpeg 路徑**: 確保 FFmpeg 已正確安裝並添加到系統環境變量 `Path` 中。
*   **Jable TV 網站變更**: 如果 Jable TV 網站結構發生變化，此工具可能需要更新才能正常工作。

## 更新日誌

 🦕 2023/4/19 新增ffmpeg自動轉檔 v1.11   
 🏹 2023/4/19 兼容Ubuntu Server v1.10   
 🦅 2023/4/15 輸入演員鏈接，下載所有該演員相關的影片 v1.9   
 🚗 2022/1/25 下載結束後抓封面 v1.8   
 🐶 2021/6/4 更改m3u8得到方法(正則表達式) v1.7  
 🌏 2021/5/28 更新代碼讓Unix系統(Mac,linux等)能使用 v1.6  
 🍎 2021/5/27 更新爬蟲網頁方法 v1.5  
 🌳 2021/5/20 修改編碼問題 v1.4  
 🌈 2021/5/6 增加下載進度提示、修改Crypto問題 v1.3  
 ⭐ 2021/5/5 更新穩定版本 v1.2  

---

如果覺得好用，請考慮給項目一個 Star！謝謝！
