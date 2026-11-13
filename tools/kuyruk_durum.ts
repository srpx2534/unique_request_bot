/**
 * Kuyruk durumunu yazar. İşler birikmişse ve aktif sıfırsa tüketici ölüdür.
 * Kullanım: npx tsx tools/kuyruk_durum.ts
 */
import "dotenv/config";
import { kuyruk } from "../src/server/kuyruk.js";

const say = async () => ({
  bekleyen: await kuyruk.getWaitingCount(),
  gecikmis: await kuyruk.getDelayedCount(),
  aktif: await kuyruk.getActiveCount(),
  basarisiz: await kuyruk.getFailedCount(),
  tamam: await kuyruk.getCompletedCount(),
});

say()
  .then(async (s) => {
    console.log(s);
    const son = await kuyruk.getFailed(0, 3);
    for (const is of son) console.log("hata:", is.failedReason);
    const bekleyen = await kuyruk.getWaiting(0, 3);
    for (const is of bekleyen) console.log("bekleyen:", is.data.kelime, is.data.tier);
    process.exit(0);
  })
  .catch((h: Error) => {
    console.error(h.message);
    process.exit(1);
  });