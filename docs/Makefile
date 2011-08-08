FOP = ~/Development/libs/fop-1.0/fop

html: reports.html

reports.html: reports.xml
	xsltproc /usr/share/sgml/docbook/xsl-stylesheets/xhtml/docbook.xsl reports.xml > reports.html

pdf: reports.pdf

reports.pdf: reports.fo
	$(FOP) reports.fo reports.pdf

reports.fo: reports.xml
	xsltproc /usr/share/sgml/docbook/xsl-stylesheets/fo/docbook.xsl reports.xml > reports.fo
