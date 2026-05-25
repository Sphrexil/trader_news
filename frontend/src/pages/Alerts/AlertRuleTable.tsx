import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { AlertRuleItem } from "@/types/models";
import { Bell, Pencil, Trash2 } from "lucide-react";

interface Props {
  items: AlertRuleItem[] | undefined;
  isLoading: boolean;
  onEdit: (item: AlertRuleItem) => void;
  onDelete: (id: number) => void;
  onTest: (id: number) => void;
  onToggle: (id: number, isActive: boolean) => void;
}

export function AlertRuleTable({ items, isLoading, onEdit, onDelete, onTest, onToggle }: Props) {
  if (isLoading) {
    return (
      <Card className="p-4 space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </Card>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card className="p-8 text-center">
        <Bell className="mx-auto h-8 w-8 text-gray-400 dark:text-gray-600 mb-2" />
        <p className="text-gray-500 dark:text-gray-400 text-sm">暂无告警规则</p>
      </Card>
    );
  }

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>股票</TableHead>
            <TableHead>规则类型</TableHead>
            <TableHead>阈值</TableHead>
            <TableHead>方向</TableHead>
            <TableHead>渠道</TableHead>
            <TableHead>状态</TableHead>
            <TableHead className="w-32">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((r) => (
            <TableRow key={r.id}>
              <TableCell>
                <span className="font-mono text-xs">{r.ts_code}</span>
                {r.stock_name && (
                  <span className="ml-1 text-sm text-gray-600 dark:text-gray-300">{r.stock_name}</span>
                )}
              </TableCell>
              <TableCell>
                <Badge variant="secondary" className="text-[10px]">{r.rule_type}</Badge>
              </TableCell>
              <TableCell className="font-medium">{r.threshold}</TableCell>
              <TableCell>
                <Badge variant={r.direction === "above" ? "default" : "secondary"} className="text-[10px]">
                  {r.direction === "above" ? "向上" : "向下"}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="text-[10px]">{r.channel}</Badge>
              </TableCell>
              <TableCell>
                <Switch checked={r.is_active} onChange={() => {
                  // optimistic via parent
                }} onClick={() => onToggle(r.id, !r.is_active)} />
              </TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onTest(r.id)}>
                    <Bell size={14} />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(r)}>
                    <Pencil size={14} />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onDelete(r.id)}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
