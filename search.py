import sqlite3
import os
import sys

# 資料庫路徑
DB_PATH = "D:\\jable\\spider_for_jable.tv\\test.db"

def search_videos_in_python(keyword):
    """在 Python 中進行過濾搜尋"""
    try:
        # 連接資料庫
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 獲取所有記錄
        cursor.execute("SELECT fanhao, url, title FROM av_db")
        all_records = cursor.fetchall()
        
        # 關閉資料庫連接
        cursor.close()
        conn.close()
        
        # 在 Python 中進行過濾
        keyword_lower = keyword.lower()  # 轉為小寫以進行不區分大小寫的搜尋
        results = []
        
        for record in all_records:
            fanhao, url, title = record
            # 檢查標題或番號是否包含關鍵字
            if ((title and keyword_lower in title.lower()) or 
                (fanhao and keyword_lower in fanhao.lower())):
                results.append(record)
        
        return results
    except Exception as e:
        print(f"搜尋時發生錯誤: {e}")
        return []

def export_to_file(keyword, results):
    """將搜尋結果匯出到檔案"""
    try:
        # 創建輸出檔案名稱
        filename = f"{keyword}.txt"
        
        # 寫入搜尋結果
        with open(filename, "w", encoding="utf-8") as f:
            # 寫入標題行
            f.write(f"關鍵字 '{keyword}' 的搜尋結果:\n")
            f.write("=" * 80 + "\n\n")
            
            # 寫入每個搜尋結果
            for i, (fanhao, url, title) in enumerate(results, 1):
                f.write(f"{i}. {title}\n")
                f.write(f"   番號: {fanhao}\n")
                f.write(f"   網址: {url}\n")
                f.write("\n")
            
            # 寫入統計資訊
            f.write("-" * 80 + "\n")
            f.write(f"共找到 {len(results)} 個符合關鍵字 '{keyword}' 的影片\n")
            
            # 添加方便複製的 URL 列表
            f.write("\n\n方便複製的 URL 列表:\n")
            for fanhao, url, title in results:
                f.write(f"{url}\n")
        
        print(f"搜尋結果已匯出到檔案: {filename}")
        return True
    except Exception as e:
        print(f"匯出檔案時發生錯誤: {e}")
        return False

def main():
    # 檢查資料庫是否存在
    if not os.path.exists(DB_PATH):
        print(f"錯誤: 找不到資料庫檔案 {DB_PATH}")
        return
    
    # 取得搜尋關鍵字
    if len(sys.argv) > 1:
        # 從命令列參數獲取關鍵字
        keyword = sys.argv[1]
    else:
        # 從使用者輸入獲取關鍵字
        keyword = input("請輸入搜尋關鍵字: ").strip()
    
    if not keyword:
        print("錯誤: 關鍵字不能為空")
        return
    
    print(f"正在搜尋關鍵字: {keyword}")
    
    # 使用 Python 進行搜尋
    results = search_videos_in_python(keyword)
    
    if results:
        print(f"找到 {len(results)} 個符合的影片")
        
        # 匯出搜尋結果
        export_to_file(keyword, results)
    else:
        print(f"找不到符合關鍵字 '{keyword}' 的影片")
        
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

if __name__ == "__main__":
    main()
