-- Olcum-B profil havuzu: profil basina kullanim sayaci (35).
-- KULLANIM_SINIRI asilinca profil yakilir, havuz kucuk kalir.
ALTER TABLE profile ADD COLUMN kullanim INT UNSIGNED NOT NULL DEFAULT 0 AFTER geo_code;