-- GA4 Measurement Protocol kimligi: hit'in Google'a gorunmesi icin.
-- Ikisi de bos ise beacon atlanir, hit yine gider.
ALTER TABLE site
    ADD COLUMN ga_id VARCHAR(32) NULL AFTER domain,
    ADD COLUMN ga_secret VARCHAR(64) NULL AFTER ga_id;