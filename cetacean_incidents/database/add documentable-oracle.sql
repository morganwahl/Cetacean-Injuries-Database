-- for Oracle

-- assumes there aren't more than 1000 animals, cases, and observations.

/*
 * create the sequence DOCUMENTS_DOCUMENTABLE_SQ with start value of 4000
 * change the trigger INCIDENTS_ANIMALS_TR to use DOCUMENTS_DOCUMENTABLE_SQ
 * change the trigger INCIDENTS_CASE_TR to use DOCUMENTS_DOCUMENTABLE_SQ
 * change the trigger INCIDENTS_OBSERVATION_TR to use DOCUMENTS_DOCUMENTABLE_SQ
 */

-- Animal
alter table INCIDENTS_ANIMAL add "DOCUMENTABLE_PTR_ID" NUMBER(11) REFERENCES "DOCUMENTS_DOCUMENTABLE" ("ID") DEFERRABLE INITIALLY DEFERRED;

insert into DOCUMENTS_DOCUMENTABLE (select DOCUMENTABLE_PTR_ID from INCIDENTS_ANIMAL);

update INCIDENTS_ANIMAL set DOCUMENTABLE_PTR_ID = ID + 1000 where ID < 4000;
update INCIDENTS_ANIMAL set DOCUMENTABLE_PTR_ID = ID where ID > 4000;

alter table INCIDENTS_ANIMAL modify (DOCUMENTABLE_PTR_ID NOT NULL); 

/*
 * remove foreign-key constraint on INCIDENTS_CASE.ANIMAL_ID
 */

/*
 * chamge primary-key of INCIDENTS_ANIMAL from ID to DOCUMENTABLE_PTR_ID
 */
 
alter table INCIDENTS_ANIMAL drop column ID;

update INCIDENTS_CASE set ANIMAL_ID = ANIMAL_ID + 1000 where ID < 4000;
alter table INCIDENTS_CASE add foreign key (ANIMAL_ID) references "INCIDENTS_ANIMAL" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

-- Case

alter table INCIDENTS_CASE add "DOCUMENTABLE_PTR_ID" NUMBER(11) REFERENCES "DOCUMENTS_DOCUMENTABLE" ("ID") DEFERRABLE INITIALLY DEFERRED;

update INCIDENTS_CASE set DOCUMENTABLE_PTR_ID = ID + 2000 where ID < 4000;
update INCIDENTS_CASE set DOCUMENTABLE_PTR_ID = ID where ID > 4000;

insert into DOCUMENTS_DOCUMENTABLE (select DOCUMENTABLE_PTR_ID from INCIDENTS_CASE);

alter table INCIDENTS_CASE modify (DOCUMENTABLE_PTR_ID NOT NULL); 

/*
 * remove foreign-key constraint on INCIDENTS_OBSERVATION.CASE_ID
 * remove foreign-key constraint on INCIDENTS_YEARCASENUMBER.CASE_ID
 * remove foreign-key constraint on ENTANGLEMENTS_ENTANGLEMENT.CASE_PTR_ID
 * remove foreign-key constraint on SHIPSTRIKES_SHIPSTRIKE.CASE_PTR_ID
 */

/*
 * chamge primary-key of INCIDENTS_CASE from ID to DOCUMENTABLE_PTR_ID
 */
 
alter table INCIDENTS_CASE drop column ID;

update INCIDENTS_OBSERVATION set CASE_ID = CASE_ID + 2000 where CASE_ID < 4000;
alter table INCIDENTS_OBSERVATION add foreign key (CASE_ID) references "INCIDENTS_CASE" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update INCIDENTS_YEARCASENUMBER set CASE_ID = CASE_ID + 2000 where CASE_ID < 4000;
alter table INCIDENTS_YEARCASENUMBER add foreign key (CASE_ID) references "INCIDENTS_CASE" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update ENTANGLEMENTS_ENTANGLEMENT set CASE_PTR_ID = CASE_PTR_ID + 2000 where CASE_PTR_ID < 4000;
alter table ENTANGLEMENTS_ENTANGLEMENT add foreign key (CASE_PTR_ID) references "INCIDENTS_CASE" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update SHIPSTRIKES_SHIPSTRIKE set CASE_PTR_ID = CASE_PTR_ID + 2000 where CASE_PTR_ID < 4000;
alter table SHIPSTRIKES_SHIPSTRIKE add foreign key (CASE_PTR_ID) references "INCIDENTS_CASE" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

-- Observations

alter table INCIDENTS_OBSERVATION add "DOCUMENTABLE_PTR_ID" NUMBER(11) REFERENCES "DOCUMENTS_DOCUMENTABLE" ("ID") DEFERRABLE INITIALLY DEFERRED;

update INCIDENTS_OBSERVATION set DOCUMENTABLE_PTR_ID = ID + 3000 where ID < 4000;
update INCIDENTS_OBSERVATION set DOCUMENTABLE_PTR_ID = ID where ID > 4000;

insert into DOCUMENTS_DOCUMENTABLE (select DOCUMENTABLE_PTR_ID from INCIDENTS_OBSERVATION);

alter table INCIDENTS_OBSERVATION modify (DOCUMENTABLE_PTR_ID NOT NULL); 

/*
 * remove foreign-key constraint on ENTANGLEMENTS_ENTANGLEMENT4F56.OBSERVATION_PTR_ID
 * remove foreign-key constraint on ENTANGLEMENTS_GEARBODYLOCATION.OBSERVATION_ID
 * remove foreign-key constraint on SHIPSTRIKES_SHIPSTRIKEOBSE6C71.OBSERVATION_PTR_ID
 */

/*
 * chamge primary-key of INCIDENTS_OBSERVATION from ID to DOCUMENTABLE_PTR_ID
 */
 
alter table INCIDENTS_OBSERVATION drop column ID;

update ENTANGLEMENTS_ENTANGLEMENT4F56 set OBSERVATION_PTR_ID = OBSERVATION_PTR_ID + 3000 where OBSERVATION_PTR_ID < 4000;
alter table ENTANGLEMENTS_ENTANGLEMENT4F56 add foreign key (OBSERVATION_PTR_ID) references "INCIDENTS_OBSERVATION" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

update ENTANGLEMENTS_GEARBODYLOCATION set OBSERVATION_ID = OBSERVATION_ID + 3000 where OBSERVATION_ID < 4000;
alter table ENTANGLEMENTS_GEARBODYLOCATION add foreign key (OBSERVATION_ID) references "ENTANGLEMENTS_ENTANGLEMENT4F56" ("OBSERVATION_PTR_ID") DEFERRABLE INITIALLY DEFERRED;


update SHIPSTRIKES_SHIPSTRIKEOBSE6C71 set OBSERVATION_PTR_ID = OBSERVATION_PTR_ID + 3000 where OBSERVATION_PTR_ID < 4000;
alter table SHIPSTRIKES_SHIPSTRIKEOBSE6C71 add foreign key (OBSERVATION_PTR_ID) references "INCIDENTS_OBSERVATION" ("DOCUMENTABLE_PTR_ID") DEFERRABLE INITIALLY DEFERRED;

/*
 * drop trigger INCIDENTS_ANIMAL_TR
 * drop trigger INCIDENTS_CASE_TR
 * drop trigger INCIDENTS_OBSERVATION_TR
 */

