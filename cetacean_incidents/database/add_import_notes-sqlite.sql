-- add import_notes column to incidents_animal, incidents_case
/* note that the DEFAULT clause isn't generated by Django's table def, but makes
 * sense.
 */
alter table "incidents_animal"
add "import_notes" text NOT NULL DEFAULT ""
;
alter table "incidents_case"
add "import_notes" text NOT NULL DEFAULT ""
;
