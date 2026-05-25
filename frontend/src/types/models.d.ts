/** 股票基础信息 */
export interface StockBrief {
  ts_code: string;
  name: string;
  market: string;
  industry: string | null;
  list_date: string | null;
  total_mv: number | null;
  circ_mv: number | null;
  pct_chg: number | null;
}

/** 个股详情 */
export interface StockInfo {
  ts_code: string;
  name: string;
  market: string;
  industry: string | null;
  list_date: string | null;
  total_share: number | null;
  float_share: number | null;
  is_listed: boolean;
}

/** 实时行情快照 */
export interface Quote {
  ts_code: string;
  name: string;
  price: number | null;
  pre_close: number | null;
  pct_chg: number | null;
  change: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  vol: number | null;
  amount: number | null;
  turnover_rate: number | null;
  total_mv: number | null;
  circ_mv: number | null;
  quote_time: string | null;
  is_trading: boolean;
}

/** K线数据 */
export interface KlineItem {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  vol: number | null;
  amount: number | null;
  pct_chg: number | null;
  turnover_rate: number | null;
  total_mv: number | null;
}

export interface KlineData {
  ts_code: string;
  period: string;
  adjust: string;
  items: KlineItem[];
  count: number;
}

/** 大盘概况 */
export interface MarketOverview {
  indices: IndexItem[];
  market_stats: MarketStats;
  updated_at: string | null;
}

export interface IndexItem {
  code: string;
  name: string;
  price: number | null;
  pct_chg: number | null;
  change: number | null;
  vol: number | null;
}

export interface MarketStats {
  up_count: number;
  down_count: number;
  flat_count: number;
  limit_up: number;
  limit_down: number;
  total_amount: number | null;
}

/** 板块 */
export interface SectorItem {
  name: string;
  pct_chg: number | null;
  change_amount: number | null;
  up_count: number;
  down_count: number;
  lead_stock: LeadStock | null;
}

export interface LeadStock {
  ts_code: string;
  name: string;
  pct_chg: number | null;
}

export interface SectorData {
  type: string;
  items: SectorItem[];
  updated_at: string | null;
}

/** 财务 */
export interface FinancialItem {
  period: string;
  report_type?: string;
  net_profit: number | null;
  net_profit_yoy: number | null;
  revenue: number | null;
  revenue_yoy: number | null;
  eps: number | null;
  deducted_profit: number | null;
  deducted_yoy: number | null;
}

export interface FinancialAnalysis {
  items: FinancialItem[];
  risk_flags: string[];
  earnings_verdict: string;
  latest_summary: string;
}

export interface FinancialData {
  ts_code: string;
  analysis: FinancialAnalysis | null;
}

/** 公告 */
export interface AnnouncementItem {
  id: number;
  ts_code: string;
  title: string;
  ann_type: string | null;
  pub_date: string;
  url: string;
  tags: string[];
  classification: string;
  has_violation: boolean;
  has_insider_sell: boolean;
  has_positive: boolean;
}
  url: string;
  summary: string | null;
}

/** 新闻 */
export interface NewsItem {
  id: number;
  source: string;
  title: string;
  url: string;
  pub_time: string;
  related_codes: string[] | null;
  sentiment: number | null;
}

// ── 自选股 ───────────────────────────────────────────

export interface WatchlistStock {
  id: number;
  ts_code: string;
  name: string;
  price: number | null;
  pct_chg: number | null;
  change: number | null;
  vol: number | null;
  cost_price: number | null;
  pnl_pct: number | null;
  note: string | null;
  added_at: string | null;
}

export interface WatchlistGroup {
  group_name: string;
  stocks: WatchlistStock[];
}

export interface WatchlistData {
  groups: WatchlistGroup[];
}

export interface WatchlistCreate {
  ts_code: string;
  group_name?: string;
  note?: string;
  cost_price?: number;
}

export interface WatchlistUpdate {
  group_name?: string;
  note?: string;
  cost_price?: number;
}

export interface WatchlistCreated {
  id: number;
  ts_code: string;
  group_name: string;
  created_at: string;
}

// ── 告警规则 ─────────────────────────────────────────

export interface AlertRuleItem {
  id: number;
  ts_code: string;
  stock_name: string | null;
  rule_type: string;
  threshold: number;
  direction: string;
  channel: string;
  channel_cfg: Record<string, unknown>;
  is_active: boolean;
  last_triggered: string | null;
  created_at: string;
}

export interface AlertRuleList {
  list: AlertRuleItem[];
}

export interface AlertRuleCreate {
  ts_code: string;
  rule_type: string;
  threshold: number;
  direction?: string;
  channel?: string;
  channel_cfg: Record<string, unknown>;
}

export interface AlertRuleUpdate {
  threshold?: number;
  is_active?: boolean;
  direction?: string;
  channel_cfg?: Record<string, unknown>;
}

export interface AlertTestResult {
  success: boolean;
  message: string;
  sent_at: string | null;
}
