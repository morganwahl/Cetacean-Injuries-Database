BEGIN;
CREATE TABLE "locations_location" (
    "id" integer NOT NULL PRIMARY KEY,
    "description" text NOT NULL,  -- a prose description of the location. if no coordinates were known at the time, this is all the location info we have; coordinates (and a large 'roughness') may be assigned later, for some simple mapping. Even if we have coordinates, the method by which they were obtained ought to be noted.
    "coordinates" varchar(127) NOT NULL, -- comma separated latitude, longitude. in decimal degrees with south and west as negative; no whitespace. 180 degrees E or W is -180. conversion from/to other formats is handled elsewhere
    "roughness" real NOT NULL -- Indicate the uncertainty of the coordinates, in meters. Should be the radius of the circle around the coordinates that contains the actual location with 95% certainty. For GPS-determined coordinates, this will be a few tens of meters. For rough estimates, note that 1 mile = 1,609.344 meters (user interfaces should handle unit conversion). When plotting locations on a map, a cirle of this size (centered at the coordinates) should be used instead of a single point, so as to not give a false sense of accuracy.
)
;
CREATE TABLE "datetime_datetime" (
    "id" integer NOT NULL PRIMARY KEY, 
    "year" integer NOT NULL, -- Year is the one required field, because without it there's no point in recording the rest
    "month" integer,
    "day" integer,
    "hour" integer, -- midnight is 0, 1pm is 13, etc. Note that all datetimes are TAI (i.e. timezoneless). It's up to the editing and display interface to convert accordingly.
    "minute" integer,
    "second" real
)
;
CREATE TABLE "contacts_organization" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(1023) NOT NULL
)
;
 -- A contact is a name of a person _or_ organization, preferably with some way of contacting them.
CREATE TABLE "contacts_contact" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(1023) NOT NULL,
    "sort_name" varchar(1023) NOT NULL, -- used for sorting by the DB. on creation, it defaults to the same as 'name' if left blank.
    "person" bool NOT NULL, -- Is this a person? (i.e. not an organization) defaults to true in the interface.

    -- Note that only one of each thing is given so that contacts just have a primary phone or email to contact them at. Other ones could be noted in 'notes' field, if necessary.
    "phone" varchar(255) NOT NULL,
    "email" varchar(255) NOT NULL,
    "address" text NOT NULL, -- mailing address

    "notes" text NOT NULL
)
;
-- this table implements a many-to-many relationship between contacts_contact and contacts_organization. The idea is to track indivdual people or orgs (whichever makes more sense as a contact for a particular observation), but still group them into sets. I.e. a contacts_contact might be for the Boston Coast Guard office, but it would have an affiliation to simple 'Coast Guard', so that one could easily answer questions like "How many reports did we get from the Coast Guard last year?"
CREATE TABLE "contacts_contact_affiliations" (
    "id" integer NOT NULL PRIMARY KEY,
    "contact_id" integer NOT NULL REFERENCES "contacts_contact" ("id"),
    "organization_id" integer NOT NULL REFERENCES "contacts_organization" ("id"),
    UNIQUE ("contact_id", "organization_id")
)
;
-- this table (it's schema and contents) was simply copied from a public domain source, and is only used for the flag field on vessels_vesselinfo
CREATE TABLE "country" (
    "iso" varchar(2) NOT NULL PRIMARY KEY,
    "name" varchar(128) NOT NULL,
    "printable_name" varchar(128) NOT NULL,
    "iso3" varchar(3),
    "numcode" smallint unsigned
)
;
-- Note that this _isn't_ a model for individual vessels, but for a description of a vessel. I.e. the same vessel will have as many vesselinfo entries as there are observations involving it.
CREATE TABLE "vessels_vesselinfo" (
    "id" integer NOT NULL PRIMARY KEY,
    "contact_id" integer REFERENCES "contacts_contact" ("id"), -- The contact for further details about the vessel, if necessary.
    "imo_number" integer, -- The International Maritime Organization number assigned to the ship. Should be a 7-digit number usually preceded with "IMO". Note that this most certainly _not_ unique, since we're just trying to capture data for _one_ observation.
    "name" varchar(255) NOT NULL,
    "flag_id" varchar(2) REFERENCES "country" ("iso"),
    "description" text NOT NULL
)
;
-- this table extends the one above (they have a one-to-one relationship) by adding fields that only matter for the striking vessel in a shipstrike
CREATE TABLE "vessels_strikingvesselinfo" (
    "vesselinfo_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "vessels_vesselinfo" ("id"),
    "length" real,
    "draft" real,
    "tonnage" real,
    "captain_id" integer REFERENCES "contacts_contact" ("id"),
    "speed" real
)
;
-- a taxon could be a Genus, a species, a Phylum, a superspecies, etc. the different entries in this table form a tree (via the supertaxon self-reference).
CREATE TABLE "taxons_taxon" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(255) NOT NULL, -- The scientific name for this taxon (i.e. the one in Latin). Genuses and above should be capitalized.
    "common_names" varchar(255) NOT NULL, -- a comma-delimited list of common English name(s) for this taxon (e.g. "humpback whale" or "dolphins, porpises"). _very_ useful in helping the user find the one they're looking for.
    "supertaxon_id" integer, -- a reference to another entry in this table. null for root-taxons.
    "rank" real NOT NULL -- a 'rank' is how specific or general this taxon is. it's a number for use in sorting, and a 'real' so that new ranks can always be added later. the mapping from a rank's name (like 'phylum', or 'subspecies') to it's number is:
    -- -1.0: species
    -- 0.0: genus
    -- 1.0: family
    -- 2.0: order
    -- for prefixes 'infra-', 'sub-', and 'super-' the ranks are changed by -0.4, -0.2, and +0.4, respectively. Thus a superspecies has rank -0.6 (-1.0 + 0.4). This is handy for displaying taxons, since ones below genus (i.e. ones with negative rank) should include all their supertaxons before them. For display genuses and above, simple use something like 'Order Oodonti'.
)
;
CREATE TABLE "incidents_animal" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(255), -- some individual animals are given names
    "determined_dead_before" date, -- useful in validating observations
    "necropsy" bool NOT NULL, -- has a necropsy been performed (shouldn't be true unless determined_dead_before is)
    "determined_gender" varchar(1) NOT NULL, -- this is the gender determined based on the one given in the obseravtions of the animal
    "determined_taxon_id" integer REFERENCES "taxons_taxon" ("id") -- ditto for taxon
)
;
-- finally, the heart of the database: observations. many of the references to other tables (specifically, observer_vessel, observation_datetime, location, and report_datetime) are one-to-one relationships. the other tables exist just to make programming easier, since they are logical sets of fields.
CREATE TABLE "incidents_observation" (
    "id" integer NOT NULL PRIMARY KEY,
    "case_id" integer NOT NULL, -- the case that this observation is part of
    "observer_id" integer REFERENCES "contacts_contact" ("id"), -- who actually saw the animal
    "observer_vessel_id" integer UNIQUE REFERENCES "vessels_vesselinfo" ("id"), -- if they were on a vessel
    "observation_datetime_id" integer NOT NULL UNIQUE REFERENCES "datetime_datetime" ("id"), -- when did they see it? (strictly, the start of the observation)
    "location_id" integer UNIQUE REFERENCES "locations_location" ("id"), -- where did they see it? (strictly, where did they observation begin)
    "reporter_id" integer REFERENCES "contacts_contact" ("id"), -- who told us about it?
    "report_datetime_id" integer NOT NULL UNIQUE REFERENCES "datetime_datetime" ("id"), -- when did we here about it? (the report_datetime of the first observation added to a case is the one used for the case itself, i.e. when assigning a yearly_number)
    "taxon_id" integer REFERENCES "taxons_taxon" ("id"), -- the most specific taxon the animal is described as
    "gender" varchar(1) NOT NULL,
    "animal_description" text NOT NULL,
    "biopsy" bool NOT NULL, -- was a biopsy sample taken?
    "wounded" bool,
    "wound_description" text NOT NULL
)
;
CREATE TABLE "incidents_case" (
    "id" integer NOT NULL PRIMARY KEY,
    "animal_id" integer NOT NULL REFERENCES "incidents_animal" ("id"),
    "ole_investigation" bool NOT NULL, -- is there a Office of Law Enforcement investigation
    "yearly_number" integer, -- a number assigned once an observation for this case is added (since that's where the date comes from). 
    "names" varchar(2048) NOT NULL -- a comma-delimited list of Case names that could refer to this case.
    -- the current name for a case is of the form:
    -- "<year>#<yearly_number> (<date>) <type> of <taxon>
    -- where <year> and <date> are determined by the earliest report_datetime of it's observations, <type> is 'Entanglement' for all entanglements, and <taxon> is the most general one that includes all the ones mentioned in observations. Note that a case may have multiple names because many of these elements could change as observations are added or updated, however each Case name should always refer to a specific case.
)
;
-- an extension of the incidents_observation table for entanglement-specific fields
CREATE TABLE "incidents_entanglementobservation" (
    "observation_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "incidents_observation" ("id"),
    "outcome" text NOT NULL
)
;
-- have a row reference it in this table marks a case as an entanglement. if any entanglement-case specific fields are needed, they will be here.
CREATE TABLE "incidents_entanglement" (
    "case_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "incidents_case" ("id")
)
;
CREATE TABLE "incidents_shipstrikeobservation" (
    "observation_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "incidents_observation" ("id"),
    "striking_vessel_id" integer REFERENCES "vessels_strikingvesselinfo" ("vesselinfo_ptr_id")
)
;
CREATE TABLE "incidents_shipstrike" (
    "case_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "incidents_case" ("id")
)
;
COMMIT;
