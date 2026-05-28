import type { PaginatedData } from "@/types/api";
import type { NewsItem } from "@/types/models";
import client from "./client";

export const newsApi = {
  search: (params: Record<string, unknown>) =>
    client.get<PaginatedData<NewsItem>>("/news", { params }),
};
