-- Fixed-width canonical values must retain trailing spaces exactly.
-- PostgreSQL char(n) ignores trailing spaces in length(), so use text here.

ALTER TABLE milstrip_app.milstrip_record
    ALTER COLUMN canonical_record TYPE text
    USING canonical_record::text;