FOP := fop
XSLT := xsltproc --xinclude

XSLT_DIR := /usr/share/xml/docbook/stylesheet/docbook-xsl

STYLESHEET := manual.css
HTML_PARAMS := --stringparam html.stylesheet $(STYLESHEET)

BUILD_DIR := built

# implicit rules
%.html: %.docbook $(STYLESHEET)
	$(XSLT) $(HTML_PARAMS) $(XSLT_DIR)/html/docbook.xsl $< > $(BUILD_DIR)/$@

%.pdf: %.fo
	$(FOP) -c "fop config.xml" $(BUILD_DIR)/$< $(BUILD_DIR)/$@
%.fo: %.docbook custom-fo.xsl
	$(XSLT) custom-fo.xsl $< > $(BUILD_DIR)/$@


all: html pdf

html: includes manual.html

pdf: includes manual.pdf

includes: TRT\ example.html api.docbook

$(BUILD_DIR):
	mkdir $(BUILD_DIR)


PROJECT_DIR := ..
API_DOCS_DIR := api_docs

$(API_DOCS_DIR):
	mkdir $(API_DOCS_DIR)

# TODO how to get this rule to depend on the actual model files?
$(API_DOCS_DIR)/%.docbook: $(PROJECT_DIR)/cetacean_incidents/apps/describe_fields/management/commands/document_fields.py | $(API_DOCS_DIR)
	env \
		PYTHONPATH=$(PROJECT_DIR) \
		DJANGO_SETTINGS_MODULE="cetacean_incidents" \
	$(PROJECT_DIR)/cetacean_incidents/manage.py \
		document_fields \
		$* > $(API_DOCS_DIR)/$*.docbook

api.docbook: \
	$(API_DOCS_DIR)/contacts.docbook \
	$(API_DOCS_DIR)/documents.docbook \
	$(API_DOCS_DIR)/entanglements.docbook \
	$(API_DOCS_DIR)/incidents.docbook \
	$(API_DOCS_DIR)/locations.docbook \
	$(API_DOCS_DIR)/shipstrikes.docbook \
	$(API_DOCS_DIR)/taxons.docbook \
	$(API_DOCS_DIR)/vessels.docbook \
	api.docbook-prefix \
	api.docbook-suffix \
	
	cat api.docbook-prefix > api.docbook
	cat $(API_DOCS_DIR)/* >> api.docbook
	cat api.docbook-suffix >> api.docbook


.PHONY: clean
clean:
	rm -rv $(HTML_DIR) $(PDF_DIR)

