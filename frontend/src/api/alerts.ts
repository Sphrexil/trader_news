import type {
  AlertRuleCreate,
  AlertRuleItem,
  AlertRuleList,
  AlertRuleUpdate,
  AlertTestResult,
} from "@/types/models";
import client from "./client";

export const alertsApi = {
  getAll: () => client.get<AlertRuleList>("/alerts"),

  create: (body: AlertRuleCreate) => client.post<AlertRuleItem>("/alerts", body),

  update: (id: number, body: AlertRuleUpdate) =>
    client.put<AlertRuleItem>(`/alerts/${id}`, body),

  remove: (id: number) =>
    client.delete<{ deleted_id: number }>(`/alerts/${id}`),

  test: (id: number) =>
    client.post<AlertTestResult>(`/alerts/test/${id}`),
};
