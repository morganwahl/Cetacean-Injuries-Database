-- rename table ENTANGLEMENTS_ENTANGLEMENT94B6 to ENTANGLEMENTS_ENTANGLEMENT8BE6
alter table ENTANGLEMENTS_ENTANGLEMENT94B6 rename to ENTANGLEMENTS_ENTANGLEMENT8BE6;
-- rename column ENTANGLEMENTS_ENTANGLEMENT8BE6.GEARTYPE_ID to GEARATTRIBUTE_ID
alter table ENTANGLEMENTS_ENTANGLEMENT8BE6 rename column "GEARTYPE_ID" to GEARATTRIBUTE_ID;
-- rename column ENTANGLEMENTS_ENTANGLEMENT54D9.GEARTYPE_ID to GEARATTRIBUTE_ID
alter table ENTANGLEMENTS_ENTANGLEMENT54D9 rename column "GEARTYPE_ID" to GEARATTRIBUTE_ID;
