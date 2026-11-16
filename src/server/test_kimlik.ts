/**
 * Test kimlik bilgileri.
 *
 * Panel testleri gerçek giriş yapar; e-posta ve parola kodda sabit durmaz.
 * İkisi `TEST_EPOSTA` ve `TEST_PAROLA` ortam değişkenlerinden okunur,
 * böylece geçici kullanıcı silinip yenisi kurulduğunda kod değişmez.
 */

/**
 * Kimlik bilgilerini ortamdan okur.
 *
 * @returns E-posta ve parola.
 * @throws Değişkenlerden biri boşsa; testin sessizce 401 almasındansa
 *     burada açık hata vermesi yeğlenir.
 */
export function kimlik(): { eposta: string; parola: string } {
  const eposta = process.env.TEST_EPOSTA ?? "";
  const parola = process.env.TEST_PAROLA ?? "";
  if (!eposta || !parola) {
    throw new Error("TEST_EPOSTA ve TEST_PAROLA tanımlı değil; .env içine ekle");
  }
  return { eposta, parola };
}
