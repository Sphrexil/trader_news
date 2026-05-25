import type { MarketOverview, SectorData } from "@/types/models";
import client from "./client";

export const marketApi = {
  getOverview: () => client.get<MarketOverview>("/market/overview"),

  getSectors: (type: string = "industry") =>
    client.get<SectorData>("/market/sectors", { params: { type } }),
};
