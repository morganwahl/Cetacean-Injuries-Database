-- add nmfs_id column to entanglements_entanglement
alter table ENTANGLEMENTS_ENTANGLEMENT
  add ("NMFS_ID" NVARCHAR2(255))
;

-- copy data form old column to new column
update ENTANGLEMENTS_ENTANGLEMENT set NMFS_ID = (
    select NMFS_ID
    from INCIDENTS_CASE
    where ENTANGLEMENTS_ENTANGLEMENT.CASE_PTR_ID = INCIDENTS_CASE.DOCUMENTABLE_PTR_ID
);

-- TODO check if the following returns anything:
select * 
  from INCIDENTS_CASE 
  where CASE_TYPE != 'Entanglement'
    and (NMFS_ID is not null or NMFS_ID != '')
;
select *
  from INCIDENTS_CASE 
    join ENTANGLEMENTS_ENTANGLEMENT 
    on (INCIDENTS_CASE.DOCUMENTABLE_PTR_ID = ENTANGLEMENTS_ENTANGLEMENT.CASE_PTR_ID)
  where incidents_case.nmfs_id != entanglements_entanglement.nmfs_id
;

-- remove nmfs_id column from incidents_case
ALTER TABLE "INCIDENTS_CASE" drop column "NMFS_ID";

