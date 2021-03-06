CREATE TABLE "DOCUMENTS_DOCUMENT_VISIBLE_TO" (
    "ID" NUMBER(11) NOT NULL PRIMARY KEY,
    "DOCUMENT_ID" NUMBER(11) NOT NULL,
    "USER_ID" NUMBER(11) NOT NULL REFERENCES "AUTH_USER" ("ID") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("DOCUMENT_ID", "USER_ID")
)
;

DECLARE
    i INTEGER;
BEGIN
    SELECT COUNT(*) INTO i FROM USER_CATALOG
        WHERE TABLE_NAME = 'DOCUMENTS_DOCUMENT_VISI5429_SQ' AND TABLE_TYPE = 'SEQUENCE';
    IF i = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE "DOCUMENTS_DOCUMENT_VISI5429_SQ"';
    END IF;
END;
/

CREATE OR REPLACE TRIGGER "DOCUMENTS_DOCUMENT_VISI5429_TR"
BEFORE INSERT ON "DOCUMENTS_DOCUMENT_VISIBLE_TO"
FOR EACH ROW
WHEN (new."ID" IS NULL)
    BEGIN
        SELECT "DOCUMENTS_DOCUMENT_VISI5429_SQ".nextval
        INTO :new."ID" FROM dual;
    END;
/
