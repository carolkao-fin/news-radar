# -*- coding: utf-8 -*-
"""關鍵字自動生成。

兩條路徑：
1. **詞庫展開** —— 主題名稱比對領域詞庫，補上同義詞、相關機構與英文對照。
   沒有 Groq 金鑰時就靠這個，不會只剩主題名稱一個關鍵字。
2. **從實際新聞回推** —— 試抓一次，統計實際出現的高頻詞彙，建議加入。
   這條路徑不依賴任何預先定義，主題再冷門也有用。
"""
import re
from collections import Counter

# 領域詞庫：主題名稱只要含到左邊的線索詞，就補上右邊那組關鍵字
LEXICON = {
    "半導體": ["半導體", "晶片", "晶圓", "先進製程", "台積電", "封裝測試",
               "semiconductor", "chip", "wafer", "foundry"],
    "晶片": ["晶片", "半導體", "晶圓", "先進製程", "semiconductor", "chip"],
    "關稅": ["關稅", "稅率", "課稅", "貿易壁壘", "tariff", "duty", "customs"],
    "出口管制": ["出口管制", "禁運", "管制清單", "實體清單", "技術管制",
                 "export control", "entity list", "sanctions"],
    "制裁": ["制裁", "禁運", "資產凍結", "sanctions", "embargo"],
    "供應鏈": ["供應鏈", "產業鏈", "斷鏈", "轉單", "在地生產",
               "supply chain", "reshoring", "nearshoring"],
    "碳": ["碳排", "碳費", "碳稅", "碳邊境", "減碳", "淨零", "溫室氣體",
           "carbon", "emissions", "CBAM", "net zero"],
    "cbam": ["CBAM", "碳邊境調整機制", "碳關稅", "歐盟碳邊境", "carbon border"],
    "人工智慧": ["人工智慧", "AI", "生成式", "大型語言模型", "機器學習", "演算法",
                 "artificial intelligence", "LLM", "machine learning"],
    "ai": ["AI", "人工智慧", "生成式", "大型語言模型", "機器學習",
           "artificial intelligence", "LLM", "machine learning"],
    "電動車": ["電動車", "電池", "車用", "充電樁", "EV", "battery"],
    "能源": ["能源", "電力", "再生能源", "核能", "天然氣", "光電", "風電",
             "energy", "power", "LNG", "nuclear", "renewable"],
    "風電": ["風電", "離岸風電", "再生能源", "綠電", "發電",
             "wind power", "offshore wind", "renewable"],
    "光電": ["光電", "太陽能", "綠電", "再生能源", "solar", "photovoltaic"],
    "稀土": ["稀土", "關鍵礦產", "礦產", "出口管制",
             "rare earth", "critical minerals"],
    "礦產": ["礦產", "關鍵礦產", "稀土", "critical minerals", "mining"],
    "匯率": ["匯率", "新台幣", "美元", "升值", "貶值", "央行",
             "exchange rate", "currency", "foreign exchange"],
    "通膨": ["通膨", "物價", "消費者物價", "CPI", "升息", "降息",
             "inflation", "interest rate"],
    "貿易": ["貿易", "出口", "進口", "經貿", "順差", "逆差",
             "trade", "export", "import"],
    "投資": ["投資", "外資", "併購", "設廠", "投資審查",
             "investment", "FDI", "acquisition"],
    "專利": ["專利", "智慧財產", "商標", "侵權", "patent", "intellectual property"],
    "資安": ["資安", "網路攻擊", "駭客", "個資", "勒索軟體",
             "cybersecurity", "hacking", "ransomware"],
    "生技": ["生技", "藥品", "疫苗", "臨床試驗", "醫材",
             "biotech", "pharmaceutical", "vaccine"],
    "農業": ["農業", "糧食", "農產品", "食品安全", "agriculture", "food security"],
    "稅": ["稅制", "租稅", "課稅", "稅率", "tax", "taxation"],
    "協定": ["貿易協定", "FTA", "CPTPP", "RCEP", "談判", "trade agreement"],
    "反傾銷": ["反傾銷", "傾銷", "平衡稅", "anti-dumping", "countervailing"],
    "勞動": ["勞動", "強迫勞動", "工會", "最低工資", "labour", "forced labour"],
    "移民": ["移民", "難民", "邊境", "庇護", "migration", "refugee", "asylum"],
    "選舉": ["選舉", "大選", "投票", "政黨", "election", "vote"],
    "戰爭": ["戰爭", "衝突", "停火", "軍事", "war", "conflict", "ceasefire"],
    # 國家與區域
    "中國": ["中國", "大陸", "北京", "中共", "China", "Beijing"],
    "美國": ["美國", "華府", "白宮", "川普", "United States", "Washington"],
    "歐盟": ["歐盟", "歐洲", "執委會", "European Union", "EU", "Brussels"],
    "日本": ["日本", "東京", "日圓", "Japan", "Tokyo"],
    "韓國": ["韓國", "首爾", "南韓", "Korea", "Seoul"],
    "東協": ["東協", "越南", "泰國", "印尼", "馬來西亞", "ASEAN"],
    "印度": ["印度", "新德里", "India", "New Delhi"],
    "台灣": ["台灣", "臺灣", "我國", "Taiwan"],
}

# 統計高頻詞時要略過的常見字詞
_STOPWORDS = {
    "表示", "指出", "報導", "今天", "昨天", "今年", "去年", "明年", "目前", "已經",
    "可能", "將會", "包括", "以及", "但是", "因為", "所以", "如果", "由於", "根據",
    "相關", "問題", "情況", "方面", "進行", "持續", "提供", "成為", "認為", "強調",
    "中央社", "記者", "綜合", "外電", "新聞", "公司", "市場", "產業", "國際", "全球",
    "完成", "宣布", "決定", "計畫", "推動", "發展", "影響", "增加", "減少", "提高",
    "重要", "主要", "其中", "透過", "針對", "有關", "一個", "這個", "他們", "我們",
    "日前", "近期", "未來", "分析", "預期", "指數", "表現", "上漲", "下跌", "報導指出",
    "the", "and", "for", "with", "that", "this", "from", "will", "has", "have",
    "are", "was", "were", "its", "their", "said", "says", "after", "over", "into",
    "new", "more", "than", "about", "would", "could", "also", "been", "which",
}


# 這些詞出現頻率高但幾乎沒有篩選力（台灣媒體每篇都會提到「台灣」），
# 仍然列為候選讓使用者自己判斷，但不預設勾選
TOO_BROAD = {
    "台灣", "臺灣", "我國", "中國", "大陸", "美國", "日本", "科技", "經濟",
    "政府", "企業", "國家", "世界", "業者", "廠商", "taiwan", "china",
    "china's", "work", "world", "global",
}


def is_broad_term(term):
    return term.lower() in TOO_BROAD


def expand_from_lexicon(name):
    """用領域詞庫展開主題名稱，回傳 (中文關鍵字, 英文關鍵字)。"""
    low = name.lower()
    zh, en = [], []
    for clue, terms in LEXICON.items():
        if clue.lower() in low:
            for t in terms:
                bucket = en if t.isascii() else zh
                if t not in bucket:
                    bucket.append(t)
    return zh, en


def _chinese_ngrams(text, sizes=(2, 3, 4)):
    """中文沒有空白斷詞，改用 n-gram 統計。只取連續的中文字串。"""
    out = []
    for run in re.findall(r"[一-鿿]{2,}", text):
        for n in sizes:
            for i in range(len(run) - n + 1):
                out.append(run[i:i + n])
    return out


def _english_words(text):
    return [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text)]


def suggest_from_articles(articles, existing=(), top_n=15, min_docs=2):
    """從抓到的新聞裡統計高頻詞，建議可以加入的關鍵字。

    只採計「出現在至少 min_docs 篇不同報導」的詞彙，避免單篇文章的特有名詞。
    另外會濾掉既有關鍵字的片段（例如已有「半導體」時不再建議「導體」「半導」），
    以及被更長候選詞涵蓋的短詞。
    """
    existing_list = [e for e in existing if e]
    existing_low = {e.lower() for e in existing_list}
    zh_docs, en_docs = Counter(), Counter()

    for a in articles:
        text = f'{a.get("title", "")} {a.get("summary", "") or a.get("raw_summary", "")}'
        zh_docs.update({t for t in _chinese_ngrams(text) if t not in _STOPWORDS})
        en_docs.update({w.lower() for w in _english_words(text)
                        if w.lower() not in _STOPWORDS and len(w) >= 4})

    def is_fragment_of_existing(term):
        """是既有關鍵字的一部分 → 沒有新資訊，不建議。
        反過來若候選詞「包含」既有關鍵字（更具體的詞），則保留。"""
        t = term.lower()
        return any(t != e and t in e for e in existing_low)

    def rank(counter, limit):
        pool = [(t, c) for t, c in counter.most_common(600) if c >= min_docs]
        picked = []
        for term, docs in pool:
            if term.lower() in existing_low or is_fragment_of_existing(term):
                continue
            # 若存在「更長且出現次數相當」的候選詞，那個才是完整詞彙
            if any(len(other) > len(term) and term in other and cnt >= docs - 1
                   for other, cnt in pool):
                continue
            if any(term in p for p in picked):
                continue
            picked.append(term)
            if len(picked) >= limit:
                break
        return picked

    return rank(zh_docs, top_n), rank(en_docs, max(top_n // 3, 3))
