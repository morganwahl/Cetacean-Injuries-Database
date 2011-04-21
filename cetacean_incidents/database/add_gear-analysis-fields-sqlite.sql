-- add the "entanglements_locationgearset" table
CREATE TABLE "entanglements_locationgearset" (
    "location_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "locations_location" ("id"),
    "depth" decimal,
    "depth_sigdigs" integer,
    "bottom_type" varchar(2048)
)
;
-- add a LocationGearSet for every GearOwner
insert into entanglements_locationgearset ( location_ptr_id )
select location_gear_set_id 
from entanglements_gearowner
;
-- change the reference of "entanglements_gearowner.location_gear_set_id" to "entanglements_locationgearset.location_ptr_id"
/*
CREATE TABLE "entanglements_gearowner" (
    "location_gear_set_id" integer UNIQUE REFERENCES "entanglements_locationgearset" ("location_ptr_id"),
); 
*/
alter table entanglements_gearowner
rename to entanglements_gearowner0
;
CREATE TABLE "entanglements_gearowner" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(1023),
    "person" bool,
    "phone" varchar(255) NOT NULL,
    "email" varchar(75) NOT NULL,
    "address" text NOT NULL,
    "notes" text NOT NULL,
    "datetime_set" char(20),
    "location_gear_set_id" integer UNIQUE REFERENCES "entanglements_locationgearset" ("location_ptr_id"),
    "datetime_missing" char(20)
)
;
insert into entanglements_gearowner
select *
from entanglements_gearowner0
;
drop table entanglements_gearowner0;

-- add the entanglements_gearattribute table
CREATE TABLE "entanglements_gearattribute" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(512) NOT NULL
)
;
-- add the entanglements_entanglement_gear_attributes table
CREATE TABLE "entanglements_entanglement_gear_attributes" (
    "id" integer NOT NULL PRIMARY KEY,
    "entanglement_id" integer NOT NULL,
    "gearattribute_id" integer NOT NULL REFERENCES "entanglements_gearattribute" ("id"),
    UNIQUE ("entanglement_id", "gearattribute_id")
)
;

-- add the entanglements_entanglement_gear_targets table
CREATE TABLE "entanglements_entanglement_gear_targets" (
    "id" integer NOT NULL PRIMARY KEY,
    "entanglement_id" integer NOT NULL,
    "taxon_id" integer NOT NULL REFERENCES "taxons_taxon" ("id"),
    UNIQUE ("entanglement_id", "taxon_id")
)
;

-- add 4 fields to entanglements_entanglement
alter table "entanglements_entanglement"
add "num_gear_types" integer
;
alter table "entanglements_entanglement"
add "gear_compliant" bool
;
alter table "entanglements_entanglement"
add "gear_kept" bool
;
alter table "entanglements_entanglement"
add "gear_kept_where" text
;

