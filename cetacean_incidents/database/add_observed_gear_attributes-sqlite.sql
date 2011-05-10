CREATE TABLE "entanglements_entanglement_observed_gear_attributes" (
    "id" integer NOT NULL PRIMARY KEY,
    "entanglement_id" integer NOT NULL,
    "geartype_id" integer NOT NULL REFERENCES "entanglements_geartype" ("id"),
    UNIQUE ("entanglement_id", "geartype_id")
)
;

