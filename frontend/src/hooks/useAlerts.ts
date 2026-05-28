import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { alertsApi } from "@/api/alerts";
import type { AlertRuleCreate, AlertRuleUpdate } from "@/types/models";
import toast from "react-hot-toast";

export function useAlerts() {
  const qc = useQueryClient();
  const KEY = ["alerts"];

  const query = useQuery({
    queryKey: KEY,
    queryFn: alertsApi.getAll,
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: (body: AlertRuleCreate) => alertsApi.create(body),
    onSuccess: () => {
      toast.success("告警规则创建成功");
      qc.invalidateQueries({ queryKey: KEY });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: AlertRuleUpdate }) =>
      alertsApi.update(id, body),
    onSuccess: () => {
      toast.success("告警规则更新成功");
      qc.invalidateQueries({ queryKey: KEY });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertsApi.remove(id),
    onSuccess: () => {
      toast.success("告警规则已删除");
      qc.invalidateQueries({ queryKey: KEY });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => alertsApi.test(id),
    onSuccess: (data) => {
      toast.success(data.message || "推送测试成功");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return { ...query, createMutation, updateMutation, deleteMutation, testMutation };
}
