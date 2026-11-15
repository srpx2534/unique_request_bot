/**
 * Ölçüm kuyruğu.
 *
 * BullMQ kendi bağlantısını ister; oturum istemcisiyle paylaşılmaz.
 * İşler iki kez denenir, başarısızlar bir süre saklanır.
 */
import { Queue } from "bullmq";
import { Redis } from "ioredis";
import { redisBaglanti } from "./redis_baglanti.js";


export const baglanti = new Redis({ ...redisBaglanti(), maxRetriesPerRequest: null });
baglanti.on("error", (hata) => console.error("[kuyruk]", hata.message));

export type Is = {
  campaignId: number;
  keywordId: number;
  keywordGeoId: number;
  kelime: string;
  il: number;
  tier: "core" | "normal" | "passive";
};

export const kuyruk = new Queue<Is>("olcum", {
  connection: baglanti,
  defaultJobOptions: {
    attempts: 2,
    backoff: { type: "exponential", delay: 5_000 },
    removeOnComplete: 500,
    removeOnFail: 1_000,
  },
});
