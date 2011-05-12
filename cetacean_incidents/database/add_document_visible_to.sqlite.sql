CREATE TABLE "documents_document_visible_to" (
    "id" integer NOT NULL PRIMARY KEY,
    "document_id" integer NOT NULL,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id"),
    UNIQUE ("document_id", "user_id")
)
;
