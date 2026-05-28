import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useWatchlist } from "@/hooks/useWatchlist";
import type { WatchlistCreate, WatchlistStock } from "@/types/models";
import { Plus, Star } from "lucide-react";
import { WatchlistDialog } from "./WatchlistDialog";
import { WatchlistGroupTable, WatchlistTableSkeleton } from "./WatchlistGroupTable";

export function Watchlist() {
  const { data, isLoading, addMutation, updateMutation, deleteMutation } = useWatchlist();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"add" | "edit">("add");
  const [editingStock, setEditingStock] = useState<WatchlistStock | undefined>();
  const [deletingStock, setDeletingStock] = useState<WatchlistStock | undefined>();

  const handleAdd = () => {
    setDialogMode("add");
    setEditingStock(undefined);
    setDialogOpen(true);
  };

  const handleEdit = (stock: WatchlistStock) => {
    setDialogMode("edit");
    setEditingStock(stock);
    setDialogOpen(true);
  };

  const handleSubmit = (body: WatchlistCreate) => {
    if (dialogMode === "add") {
      addMutation.mutate(body);
    } else if (editingStock) {
      updateMutation.mutate({
        id: editingStock.id,
        body: { group_name: body.group_name, cost_price: body.cost_price, note: body.note },
      });
    }
  };

  const handleDelete = (stock: WatchlistStock) => {
    setDeletingStock(stock);
  };

  const groups = data?.groups ?? [];
  const isEmpty = !isLoading && groups.length === 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">自选股</h1>
        <Button onClick={handleAdd} className="gap-1">
          <Plus size={16} />
          添加自选
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <WatchlistTableSkeleton />
          <WatchlistTableSkeleton />
        </div>
      ) : isEmpty ? (
        <div className="text-center py-16">
          <Star className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400 mb-4">暂无自选股</p>
          <Button onClick={handleAdd} className="gap-1">
            <Plus size={16} />
            添加第一只
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((g) => (
            <WatchlistGroupTable
              key={g.group_name}
              group={g}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <WatchlistDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
        mode={dialogMode}
        initial={editingStock}
      />

      <ConfirmDialog
        open={!!deletingStock}
        onClose={() => setDeletingStock(undefined)}
        onConfirm={() => {
          if (deletingStock) deleteMutation.mutate(deletingStock.id);
          setDeletingStock(undefined);
        }}
        title="删除自选股"
        description={`确定要删除 ${deletingStock?.ts_code} ${deletingStock?.name} 吗？此操作不可撤销。`}
        confirmText="删除"
      />
    </div>
  );
}
