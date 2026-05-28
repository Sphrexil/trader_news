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
    # 市场术语
    "A股", "上证", "深证", "创业板", "科创板", "北交所",
    "涨停", "跌停", "板块", "概念", "个股", "大盘",
    "沪深", "指数", "沪指", "深指", "股指",
    "券商", "基金", "机构", "游资", "主力",
    "央行", "证监会", "银保监会", "交易所", "金融监管",
    "IPO", "上市", "新股", "打新",
    "龙虎榜", "大宗交易",
    "高位", "低位", "反弹", "回调", "震荡", "牛市", "熊市",
    "股份", "股价", "收盘", "开盘",
    "业绩", "利润", "营收", "净利润",
    "政策", "监管", "注册制", "退市",
    # 行业板块
    "半导体", "芯片", "新能源", "光伏", "锂电", "储能",
    "医药", "消费", "地产", "银行", "保险",
    "汽车", "军工", "钢铁", "煤炭", "有色", "化工",
    # 宏观/金融
    "期货", "人民币", "汇率", "利率", "国债", "债券",
    "港股", "美股", "中概", "恒生", "纳斯达克",
    "通胀", "CPI", "PPI", "GDP", "PMI", "社融", "M2",
    "美联储", "欧洲央行", "加息", "降息", "降准",
    # 政策/政府
    "国务院", "国常会", "政治局", "中央经济", "中央金融",
    "发改委", "工信部", "科技部", "财政部", "商务部", "住建部",
    "国资委", "网信办", "金融委", "深改委",
    "十四五", "十五五", "规划", "行动方案", "指导意见", "通知",
    "印发", "出台", "部署", "推进", "实施",
    "改革", "开放", "营商环境", "民营经济", "国企改革",
    # 科技/AI
    "人工智能", "AI", "大模型", "算力", "算法", "数据",
    "机器人", "自动驾驶", "低空经济", "量子", "6G",
    "数字经济", "数字化转型", "工业互联网",
    # 能源/环境
    "碳中和", "碳达峰", "绿色", "减排", "环保",
    # 基础设施
    "城市更新", "基建", "新基建", "交通", "水利",
    "电网", "特高压", "数据中心", "东数西算",
    # 突发事件
    "突发", "重磅", "紧急", "刚刚", "快讯",
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
    """基于 snownlp + 关键词混合打分 (-1 到 +1)。

    优先用 snownlp 中文 NLP 情感分析，关键词辅助加权。
    """
    text = (title + " " + content).lower() if content else title.lower()

    # snownlp NLP 打分
    nlp_score = 0.0
    try:
        from snownlp import SnowNLP
        s = SnowNLP(title + content[:200] if content else title)
        nlp_score = round(s.sentiments * 2 - 1, 3)  # 0~1 → -1~1
    except Exception:
        pass

    # 关键词加权
    pos = sum(1.5 for kw in POSITIVE_KW if kw.lower() in text)
    neg = sum(1.5 for kw in NEGATIVE_KW if kw.lower() in text)

    if pos == 0 and neg == 0:
        return nlp_score

    kw_score = round((pos - neg) / max(pos + neg, 1), 3)

    # 混合：关键词权重 0.4 + NLP 权重 0.6
    return round(kw_score * 0.4 + nlp_score * 0.6, 3)


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

def hot_score(sentiment: float, relevance: float, pub_time: str = "") -> float:
    """热度 = 相关性 × 0.7 + 情感极端程度 × 0.3 × 时间衰减。

    重点放在相关性而非情感极端性，确保重要政策新闻不被漏掉。
    """
    base = relevance * 0.7 + abs(sentiment) * 0.3

    # 时间衰减（最近1小时权重1.0，每过1小时衰减0.1）
    time_factor = 1.0
    try:
        from datetime import datetime, timedelta
        ts = int(pub_time)
        if ts > 1000000000:
            age_hours = (datetime.now() - datetime.fromtimestamp(ts)).total_seconds() / 3600
            time_factor = max(0.3, 1.0 - age_hours * 0.1)
    except (ValueError, TypeError):
        pass

    return round(base * time_factor, 3)


# ── 板块关键词映射 ──────────────────────────────────────

SECTOR_KEYWORDS = {
    "房地产": ["地产", "房价", "楼盘", "城市更新", "住建部", "公积金", "房贷", "购房", "售楼", "物业", "二手房"],
    "建筑建材": ["建材", "水泥", "玻璃", "管材", "装修", "基建", "施工", "工程设计"],
    "新能源": ["光伏", "锂电", "储能", "风电", "氢能", "新能源车", "充电桩", "固态电池", "钙钛矿", "钠离子"],
    "半导体": ["芯片", "半导体", "光刻", "晶圆", "集成电路", "EDA", "先进封装", "HBM", "存储芯片", "GPU"],
    "AI科技": ["人工智能", "AI", "大模型", "算力", "算法", "机器人", "自动驾驶", "数字经济", "6G", "量子"],
    "金融": ["银行", "保险", "券商", "降准", "降息", "利率", "汇率", "LPR", "MLF", "OMO", "逆回购", "金融监管"],
    "医药": ["医药", "创新药", "疫苗", "医疗器械", "集采", "医保", "仿制药", "生物药", "CXO", "基因"],
    "消费": ["消费", "零售", "电商", "白酒", "家电", "旅游", "免税", "餐饮", "预制菜", "直播"],
    "军工航天": ["军工", "航天", "卫星", "导弹", "舰船", "战斗机", "雷达", "无人机", "低空经济"],
    "资源有色": ["煤炭", "钢铁", "铜", "铝", "稀土", "黄金", "白银", "原油", "天然气", "锂矿"],
    "农业": ["粮食", "农业", "种业", "化肥", "养殖", "水产", "转基因", "农药"],
    "电力能源": ["电力", "电网", "特高压", "核电", "火电", "水电", "绿电", "虚拟电厂", "储能电站"],
    "汽车": ["汽车", "整车", "零部件", "智能驾驶", "车联网", "比亚迪", "特斯拉", "华为汽车"],
    "交通运输": ["高铁", "铁路", "港口", "航空", "航运", "集装箱", "高速公路", "轨道交通", "地铁"],
}

BREAKING_KEYWORDS = ["突发", "重磅", "紧急", "刚刚", "快讯", "最新", "暴跌", "暴涨", "熔断", "黑天鹅"]

# 匹配6位股票代码
STOCK_CODE_RE = re.compile(r'\b[0-9]{6}\b')


# ── 个股关联 ────────────────────────────────────────────

def match_stock_codes(text: str) -> list[str]:
    """从文本中提取可能的股票代码，验证后返回 ts_code 列表。"""
    raw_codes = STOCK_CODE_RE.findall(text)
    if not raw_codes:
        return []

    unique = list(set(raw_codes))[:10]  # 最多10个
    try:
        from database import SessionLocal
        from models.stock import Stock
        db = SessionLocal()
        try:
            stocks = db.query(Stock).filter(Stock.ts_code.in_(
                [f"{c}.SH" for c in unique] + [f"{c}.SZ" for c in unique] +
                [f"{c}.BJ" for c in unique]
            )).all()
            return [s.ts_code for s in stocks]
        finally:
            db.close()
    except Exception:
        # DB 不可用时，按代码前缀推断
        result = []
        for c in unique:
            if c.startswith(("6", "68", "689")):
                result.append(f"{c}.SH")
            elif c.startswith(("0", "3", "30")):
                result.append(f"{c}.SZ")
            elif c.startswith(("8", "4")):
                result.append(f"{c}.BJ")
        return result


# ── AI 摘要 ─────────────────────────────────────────────

def generate_summary(title: str, content: str = "") -> str:
    """从标题+正文提取一句话摘要（≤60字）。

    策略：保留标题核心信息，截断过长的说明。
    """
    text = (title + "。" + content) if content else title

    # 去除多余的空白和时间前缀
    cleaned = text.strip().replace("\n", " ").replace("\r", "")
    # 截取前100字作为摘要
    if len(cleaned) <= 60:
        return cleaned
    # 尝试在句号处截断
    cutoff = cleaned[:80].rfind("。")
    if cutoff > 30:
        return cleaned[:cutoff + 1]
    cutoff = cleaned[:80].rfind("，")
    if cutoff > 30:
        return cleaned[:cutoff] + "…"
    return cleaned[:60] + "…"


# ── 投资解读 ─────────────────────────────────────────────

def analyze_impact(title: str, content: str = "", sentiment: float = 0) -> dict:
    """分析新闻对A股的影响。

    Returns:
        {"impact_sectors": str, "impact_level": str, "investment_note": str}
    """
    text = (title + " " + content).lower()
    sent_label = classify(title)["label"]

    # 匹配板块
    matched_sectors = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                matched_sectors.append(sector)
                break

    # 判断影响级别
    gov_keywords = ["国务院", "中央", "政治局", "发改委", "工信部", "证监会", "央行"]
    is_policy = any(kw in title for kw in gov_keywords) or len(matched_sectors) >= 3
    is_sector = len(matched_sectors) >= 1
    has_stock_code = bool(STOCK_CODE_RE.search(title))

    if is_policy:
        impact_level = "政策级"
    elif is_sector:
        impact_level = "行业级"
    elif has_stock_code:
        impact_level = "个股级"
    else:
        impact_level = "一般"

    # 生成投资解读
    note = _make_investment_note(
        title, sent_label, matched_sectors, impact_level
    )

    return {
        "impact_sectors": ",".join(matched_sectors[:3]) if matched_sectors else None,
        "impact_level": impact_level,
        "investment_note": note,
    }


def _make_investment_note(
    title: str, sentiment_label: str, sectors: list[str], level: str,
) -> str | None:
    """根据新闻内容生成一句话投资建议。"""
    if not sectors and level == "一般":
        return None

    direction = "利好" if sentiment_label == "利好" else ("利空" if sentiment_label == "利空" else "关注")
    sector_str = "、".join(sectors[:2]) if sectors else "相关板块"

    if level == "政策级":
        return f"{direction}{sector_str}。政策力度大，关注龙头及产业链上下游"
    elif level == "行业级":
        return f"{direction}{sector_str}，关注板块内核心标的"
    elif level == "个股级":
        code_match = STOCK_CODE_RE.search(title)
        if code_match:
            return f"{direction}个股{code_match.group()}，注意甄别基本面"
        return f"{direction}相关个股，注意甄别基本面"
    return f"{direction}{sector_str}"


# ── 突发/重磅判断 ───────────────────────────────────────

def is_breaking_news(title: str, sentiment: float = 0, relevance: float = 0) -> bool:
    """判断是否为突发/重磅新闻。"""
    # 关键词匹配
    for kw in BREAKING_KEYWORDS:
        if kw in title:
            return True
    # 政策级 + 极端情感
    gov_kw = ["国务院", "中央", "政治局", "证监会"]
    if any(kw in title for kw in gov_kw):
        return True
    # 极端情感 + 高相关
    if abs(sentiment) > 0.8 and relevance > 0.5:
        return True
    # 涨跌停等极端事件
    if any(kw in title for kw in ["涨停", "跌停", "暴跌", "暴涨", "熔断"]):
        return True
    return False


# ── 主管线 ──────────────────────────────────────────────

def process(news_items: list[dict], top_n: int = 30) -> list[dict]:
    """完整新闻处理管线。

    输入: 原始新闻列表 [{title, content, source, url, pub_time}]
    输出: 处理后新闻列表 [{..., sentiment, relevance, hot, tags, summary, impact, related_codes}]
    """
    if not news_items:
        return []

    # 1. 去重
    deduped = deduplicate(news_items)
    logger.info(f"去重: {len(news_items)} → {len(deduped)}")

    # 2. 情感 + 相关性 + 分类 + 个股关联 + 摘要 + 投资解读
    for item in deduped:
        title = item.get("title", "")
        content = item.get("content", "")

        sent = sentiment_score(title, content)
        rel = relevance_score(title)
        cls = classify(title)

        item["sentiment"] = sent
        item["relevance"] = rel
        item["hot_score"] = hot_score(sent, rel, item.get("pub_time", ""))
        item["sentiment_label"] = cls["label"]
        item["positive_matches"] = cls["positive_matches"]
        item["negative_matches"] = cls["negative_matches"]

        # 个股关联
        related = match_stock_codes(title + content)
        if related:
            item["related_codes"] = ",".join(related[:5])

        # AI 摘要
        item["summary"] = generate_summary(title, content)

        # 投资解读
        impact = analyze_impact(title, content, sent)
        item["impact_sectors"] = impact["impact_sectors"]
        item["impact_level"] = impact["impact_level"]
        item["investment_note"] = impact["investment_note"]

        # 突发/重磅
        item["is_breaking"] = is_breaking_news(title, sent, rel)

    # 3. 排序：重磅置顶 → 按热度
    deduped.sort(key=lambda x: (not x.get("is_breaking", False), -x["hot_score"]))

    return deduped[:top_n]
