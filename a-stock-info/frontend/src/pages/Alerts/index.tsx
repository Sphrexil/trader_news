import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useAlerts } from "@/hooks/useAlerts";
import type { AlertRuleCreate, AlertRuleItem } from "@/types/models";
import { Bell, Plus } from "lucide-react";
import { AlertDialog } from "./AlertDialog";
import { AlertRuleTable } from "./AlertRuleTable";

export function Alerts() {
  const { data, isLoading, createMutation, updateMutation, deleteMutation, testMutation } = useAlerts();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"add" | "edit">("add");
  const [editingItem, setEditingItem] = useState<AlertRuleItem | undefined>();
  const [deletingId, setDeletingId] = useState<number | undefined>();

  const handleAdd = () => {
    setDialogMode("add");
    setEditingItem(undefined);
    setDialogOpen(true);
  };

  const handleEdit = (item: AlertRuleItem) => {
    setDialogMode("edit");
    setEditingItem(item);
    setDialogOpen(true);
  };

  const handleSubmit = (body: AlertRuleCreate) => {
    if (dialogMode === "add") {
      createMutation.mutate(body);
    } else if (editingItem) {
      updateMutation.mutate({
        id: editingItem.id,
        body: {
          threshold: body.threshold,
          direction: body.direction,
          channel_cfg: body.channel_cfg,
        },
      });
    }
  };

  const handleDelete = (id: number) => {
    setDeletingId(id);
  };

  const handleToggle = (id: number, isActive: boolean) => {
    updateMutation.mutate({ id, body: { is_active: isActive } });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">告警管理</h1>
        <Button onClick={handleAdd} className="gap-1">
          <Plus size={16} />
          创建规则
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-md" />
          ))}
        </div>
      ) : (data?.list?.length ?? 0) === 0 ? (
        <div className="text-center py-16">
          <Bell className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400 mb-4">暂无告警规则</p>
          <Button onClick={handleAdd} className="gap-1">
            <Plus size={16} />
            创建第一条
          </Button>
        </div>
      ) : (
        <AlertRuleTable
          items={data?.list}
          isLoading={false}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onTest={(id) => testMutation.mutate(id)}
          onToggle={handleToggle}
        />
      )}

      <AlertDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
        mode={dialogMode}
        initial={editingItem}
      />

      <ConfirmDialog
        open={deletingId !== undefined}
        onClose={() => setDeletingId(undefined)}
        onConfirm={() => {
          if (deletingId !== undefined) deleteMutation.mutate(deletingId);
          setDeletingId(undefined);
        }}
        title="删除告警规则"
        description="确定要删除此告警规则吗？此操作不可撤销。"
        confirmText="删除"
      />
    </div>
  );
}
