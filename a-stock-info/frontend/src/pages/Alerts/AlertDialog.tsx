import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { AlertRuleCreate, AlertRuleItem } from "@/types/models";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (body: AlertRuleCreate) => void;
  mode: "add" | "edit";
  initial?: AlertRuleItem;
}

export function AlertDialog({ open, onClose, onSubmit, mode, initial }: Props) {
  const [tsCode, setTsCode] = useState(initial?.ts_code ?? "");
  const [ruleType, setRuleType] = useState(initial?.rule_type ?? "price_pct");
  const [threshold, setThreshold] = useState(initial?.threshold?.toString() ?? "");
  const [direction, setDirection] = useState(initial?.direction ?? "above");
  const [channel, setChannel] = useState(initial?.channel ?? "bark");
  const [channelCfg, setChannelCfg] = useState(
    initial ? JSON.stringify(initial.channel_cfg, null, 2) : "{}",
  );

  const handleSubmit = () => {
    if (!tsCode.trim()) return;
    let cfg = {};
    try {
      cfg = JSON.parse(channelCfg || "{}");
    } catch {
      cfg = {};
    }
    onSubmit({
      ts_code: tsCode.trim(),
      rule_type: ruleType,
      threshold: parseFloat(threshold) || 0,
      direction,
      channel,
      channel_cfg: cfg,
    });
    reset();
    onClose();
  };

  const reset = () => {
    if (mode === "add") {
      setTsCode("");
      setRuleType("price_pct");
      setThreshold("");
      setDirection("above");
      setChannel("bark");
      setChannelCfg("{}");
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={reset}>
      <DialogHeader>
        <DialogTitle>{mode === "add" ? "创建告警规则" : "编辑告警规则"}</DialogTitle>
        <DialogClose onClick={reset} />
      </DialogHeader>
      <div className="space-y-4 mt-4">
        <div className="space-y-2">
          <Label htmlFor="al_ts_code">股票代码</Label>
          <Input id="al_ts_code" placeholder="600000.SH" value={tsCode}
            onChange={(e) => setTsCode(e.target.value)} disabled={mode === "edit"} />
        </div>
        <div className="space-y-2">
          <Label>规则类型</Label>
          <Select value={ruleType} onChange={(e) => setRuleType(e.target.value)}>
            <option value="price_pct">涨跌幅(%)</option>
            <option value="price_abs">价格(元)</option>
            <option value="volume_ratio">量比</option>
            <option value="ann_publish">公告发布</option>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="al_threshold">阈值</Label>
          <Input id="al_threshold" type="number" step="0.01"
            value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>方向</Label>
          <Select value={direction} onChange={(e) => setDirection(e.target.value)}>
            <option value="above">向上突破</option>
            <option value="below">向下跌破</option>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>推送渠道</Label>
          <Select value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="bark">Bark</option>
            <option value="email">Email</option>
            <option value="webhook">Webhook</option>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="al_cfg">渠道配置 (JSON)</Label>
          <Input id="al_cfg" placeholder='{"bark_key":"..."}' value={channelCfg}
            onChange={(e) => setChannelCfg(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={reset}>取消</Button>
          <Button onClick={handleSubmit}>{mode === "add" ? "创建" : "保存"}</Button>
        </div>
      </div>
    </Dialog>
  );
}
