"""新闻处理管线 — 去重 → 情感打分 → 相关性过滤 → 分类 → 热度排序。

纯 Python 实现，无 GPU 依赖。
"""

import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# ── 关键词库 ─────────────────────────────────────────────

POSITIVE_KW = [
    # 业绩类
    "业绩增长", "净利润增长", "营收增长", "利润大增", "扭亏为盈",
    "业绩预增", "预盈", "超预期", "业绩大幅", "盈利提升",
    # 合同/订单
    "中标", "签约", "订单", "大单", "合同",
    # 股东行为
    "回购", "增持", "分红", "送转", "派息", "高送转", "高分红",
    # 市场表现
    "涨停", "大涨", "创新高", "突破", "领涨", "上涨", "反弹",
    # 政策利好
    "政策利好", "国家支持", "补贴", "减税", "降准", "降息",
    "产业扶持", "政策扶持", "国常会", "国务院", "出台",
    "中央经济", "政治局", "发改委", "工信部", "科技部",
    "财政刺激", "货币政策", "宽松", "定向降准",
    # 产品/技术
    "新产品", "新药获批", "专利", "技术突破", "研发成功",
    "获批上市", "获批临床", "临床试验", "量产", "发布",
    # 资本运作
    "收购", "并购", "重组", "资产注入", "借壳",
    "战投", "引入战略", "定增", "配股",
    # 产能/扩张
    "产能扩大", "扩产", "投产", "开工", "竣工",
    # 外资
    "北向资金流入", "外资增持", "外资买入", "沪股通净买入", "深股通净买入",
    # 合作
    "战略合作", "签署协议", "达成合作", "深度合作",
    # AI/科技
    "AI", "大模型", "算力", "芯片突破", "光刻", "量子",
    "人工智能", "机器人", "自动驾驶", "6G", "新能源",
    "固态电池", "钙钛矿", "核聚变", "航天", "卫星",
    # 地缘缓和
    "关系缓和", "停火", "和谈", "谈判", "协议达成", "解除制裁",
    "贸易缓和", "关税下调", "关系改善",
    # IPO/上市
    "IPO", "上市", "新股", "挂牌", "过会", "注册生效",
    # 消费/经济
    "消费回暖", "内需扩大", "经济复苏", "GDP增长",
    "社零增长", "PMI回升", "出口增长",
]

NEGATIVE_KW = [
    # 业绩类
    "业绩下滑", "净利润下降", "亏损", "预亏", "低于预期",
    "业绩变脸", "巨亏", "营收下降", "下滑",
    # 股东行为
    "减持", "股东减持", "董监高减持", "套现", "清仓", "抛售",
    # 违法/违规
    "违法", "违规", "处罚", "立案调查", "警示函", "监管函",
    "通报批评", "责令改正", "纪律处分", "行政处罚",
    "内幕交易", "操纵市场", "财务造假",
    # 市场表现
    "跌停", "大跌", "暴跌", "破发", "破净", "创新低", "下跌",
    # 财务风险
    "商誉减值", "资产减值", "计提减值", "债务违约", "逾期",
    "爆雷", "暴雷", "退市风险", "ST", "*ST",
    # 限售/解禁
    "限售解禁", "大额解禁", "解禁潮",
    # 停产/事故
    "停产", "停工", "召回", "爆炸", "火灾", "事故",
    # 外资
    "北向资金流出", "外资减持", "外资卖出", "沪股通净卖出", "深股通净卖出",
    # 诉讼
    "诉讼", "仲裁", "冻结", "查封", "破产",
    # 利空政策
    "加税", "反垄断", "制裁", "出口管制", "实体清单",
    "关税", "贸易战", "地缘风险", "军事冲突", "战争",
    # 经济下行
    "经济下行", "通缩", "衰退", "PMI下降", "社零下降",
    "失业率", "通胀", "加息",
]

A_SHARE_RELEVANCE = [
    "A股", "上证", "深证", "创业板", "科创板", "北交所",
    "涨停", "跌停", "板块", "概念",
    "沪深", "大盘", "指数", "沪指", "深指",
    "券商", "基金", "机构", "游资", "主力",
    "央行", "证监会", "银保监会", "交易所",
    "IPO", "上市", "新股", "打新",
    "龙虎榜", "大宗交易",
    "高位", "低位", "反弹", "回调", "震荡",
    # 新增
    "股份", "股价", "收盘", "开盘", "个股",
    "业绩", "利润", "营收", "净利润",
    "政策", "监管", "注册制", "退市",
    "半导体", "芯片", "新能源", "光伏", "锂电",
    "医药", "消费", "地产", "银行", "保险",
    "期货", "人民币", "汇率", "利率", "国债",
    "港股", "美股", "中概", "恒生", "纳斯达克",
]

# 匹配6位股票代码
STOCK_CODE_RE = re.compile(r'\b[0-9]{6}\b')


# ── 去重 ────────────────────────────────────────────────

def deduplicate(items: list[dict], threshold: float = 0.75) -> list[dict]:
    """基于标题相似度去重。"""
    if len(items) <= 1:
        return items

    kept = [items[0]]
    for item in items[1:]:
        title = item.get("title", "")
        is_dup = False
        for k in kept:
            ratio = SequenceMatcher(None, title, k.get("title", "")).ratio()
            if ratio > threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(item)
    return kept


# ── 情感打分 ────────────────────────────────────────────

def sentiment_score(title: str, content: str = "") -> float:
    """基于关键词的情感打分 (-1 到 +1)。"""
    text = (title + " " + content).lower() if content else title.lower()

    pos = sum(2 if kw.lower() in text else 0 for kw in POSITIVE_KW)
    neg = sum(2 if kw.lower() in text else 0 for kw in NEGATIVE_KW)

    if pos == 0 and neg == 0:
        # 尝试 snownlp
        try:
            from snownlp import SnowNLP
            s = SnowNLP(title)
            return round(s.sentiments * 2 - 1, 3)  # 0~1 → -1~1
        except ImportError:
            return 0.0

    total = pos + neg
    return round((pos - neg) / total, 3) if total > 0 else 0.0


# ── 相关性 ──────────────────────────────────────────────

def relevance_score(title: str) -> float:
    """A股相关性打分 (0 到 1)。"""
    score = 0.0

    # 匹配股票代码
    if STOCK_CODE_RE.search(title):
        score += 0.3

    # 关键词匹配
    for kw in A_SHARE_RELEVANCE:
        if kw in title:
            score += 0.15
            if score >= 1.0:
                return 1.0

    # 有涨跌幅数字
    if re.search(r'[+-]?\d+\.?\d*%', title):
        score += 0.1

    return min(score, 1.0)


# ── 分类 ────────────────────────────────────────────────

def classify(title: str) -> dict:
    """分类：利好/利空/中性，附匹配的关键词。"""
    pos_hits = [kw for kw in POSITIVE_KW if kw in title]
    neg_hits = [kw for kw in NEGATIVE_KW if kw in title]

    if pos_hits and not neg_hits:
        label = "利好"
    elif neg_hits and not pos_hits:
        label = "利空"
    elif pos_hits and neg_hits:
        label = "利好" if len(pos_hits) > len(neg_hits) else "利空"
    else:
        label = "中性"

    return {
        "label": label,
        "positive_matches": pos_hits[:5],
        "negative_matches": neg_hits[:5],
    }


# ── 热度排序 ────────────────────────────────────────────

def hot_score(sentiment: float, relevance: float) -> float:
    """热度 = 情感极端程度 × 相关性。

    情感极端（大涨/暴跌）的新闻比中性新闻更有价值。
    """
    return round(abs(sentiment) * 0.6 + relevance * 0.4, 3)


# ── 主管线 ──────────────────────────────────────────────

def process(news_items: list[dict], top_n: int = 30) -> list[dict]:
    """完整新闻处理管线。

    输入: 原始新闻列表 [{title, content, source, url, pub_time}]
    输出: 处理后新闻列表 [{..., sentiment, relevance, hot, tags}]
    """
    if not news_items:
        return []

    # 1. 去重
    deduped = deduplicate(news_items)
    logger.info(f"去重: {len(news_items)} → {len(deduped)}")

    # 2. 情感 + 相关性 + 分类
    for item in deduped:
        title = item.get("title", "")
        content = item.get("content", "")

        sent = sentiment_score(title, content)
        rel = relevance_score(title)
        cls = classify(title)

        item["sentiment"] = sent
        item["relevance"] = rel
        item["hot_score"] = hot_score(sent, rel)
        item["sentiment_label"] = cls["label"]
        item["positive_matches"] = cls["positive_matches"]
        item["negative_matches"] = cls["negative_matches"]

    # 3. 按热度排序
    deduped.sort(key=lambda x: x["hot_score"], reverse=True)

    return deduped[:top_n]
