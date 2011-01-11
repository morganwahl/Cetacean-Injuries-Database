-- for sqlite

alter table "incidents_observation" 
add "animal_id" integer REFERENCES "incidents_animal" ("documentable_ptr_id")
;

update incidents_observation 
set animal_id = (
  select animal_id 
  from incidents_case 
  where incidents_case.documentable_ptr_id = incidents_observation.case_id
)
;

CREATE TABLE "incidents_observation_cases" (
    "id" integer NOT NULL PRIMARY KEY,
    "observation_id" integer NOT NULL,
    "case_id" integer NOT NULL,
    UNIQUE ("observation_id", "case_id")
)
;

insert into incidents_observation_cases 
( observation_id, case_id )
select io.documentable_ptr_id, io.case_id
from incidents_observation as io
;

-- should do this, but can't in sqlite
/*
alter table incidents_observation 
drop column case_id
;
*/
