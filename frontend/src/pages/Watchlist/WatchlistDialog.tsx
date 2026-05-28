import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { WatchlistCreate, WatchlistStock, WatchlistUpdate } from "@/types/models";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (body: WatchlistCreate) => void;
  mode: "add" | "edit";
  initial?: WatchlistStock;
}

export function WatchlistDialog({ open, onClose, onSubmit, mode, initial }: Props) {
  const [tsCode, setTsCode] = useState(initial?.ts_code ?? "");
  const [groupName, setGroupName] = useState("默认");
  const [costPrice, setCostPrice] = useState(initial?.cost_price?.toString() ?? "");
  const [note, setNote] = useState(initial?.note ?? "");

  const handleSubmit = () => {
    if (!tsCode.trim()) return;
    onSubmit({
      ts_code: tsCode.trim(),
      group_name: groupName || "默认",
      cost_price: costPrice ? parseFloat(costPrice) : undefined,
      note: note || undefined,
    });
    reset();
    onClose();
  };

  const reset = () => {
    if (mode === "add") {
      setTsCode("");
      setGroupName("默认");
      setCostPrice("");
      setNote("");
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={reset}>
      <DialogHeader>
        <DialogTitle>{mode === "add" ? "添加自选股" : "编辑自选股"}</DialogTitle>
        <DialogClose onClick={reset} />
      </DialogHeader>
      <div className="space-y-4 mt-4">
        <div className="space-y-2">
          <Label htmlFor="ts_code">股票代码</Label>
          <Input
            id="ts_code"
            placeholder="如 600000.SH"
            value={tsCode}
            onChange={(e) => setTsCode(e.target.value)}
            disabled={mode === "edit"}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="group">分组</Label>
          <Input
            id="group"
            placeholder="默认"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cost">成本价（可选）</Label>
          <Input
            id="cost"
            type="number"
            step="0.01"
            placeholder="0.00"
            value={costPrice}
            onChange={(e) => setCostPrice(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="note">备注（可选）</Label>
          <Input
            id="note"
            placeholder="备注信息"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={reset}>取消</Button>
          <Button onClick={handleSubmit}>{mode === "add" ? "添加" : "保存"}</Button>
        </div>
      </div>
    </Dialog>
  );
}
