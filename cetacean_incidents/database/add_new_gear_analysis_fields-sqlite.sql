-- add the three new fields
alter table "entanglements_entanglement"
add "gear_description" text
;

alter table "entanglements_entanglement"
add "gear_analysis_comments" text
;

alter table "entanglements_entanglement"
add "gear_analysis_conclusions" text
;

-- copy values from the one old field
update entanglements_entanglement 
  set gear_description = (
    select missing_gear 
    from entanglements_gearowner 
    where id = entanglements_entanglement.gear_owner_info_id
  )
;

-- drop the old field
# TODO how to drop a column in SQLite?

