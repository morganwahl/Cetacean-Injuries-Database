FOP := fop -q
XSLT := xsltproc --xinclude

XSLT_DIR := /usr/share/xml/docbook/stylesheet/docbook-xsl

STYLESHEET := manual.css
HTML_PARAMS := --stringparam html.stylesheet $(STYLESHEET)

BUILD_DIR := ../cetacean_incidents/site_media/manual

MANUAL_DEPENDS := TRT\ example.html api.docbook reports.docbook ui.docbook

.PHONEY: all html pdf

all: html pdf

html: $(BUILD_DIR)/manual.html $(BUILD_DIR)/manual.css

$(BUILD_DIR)/manual.html: manual.docbook $(MANUAL_DEPENDS) | $(BUILD_DIR)
	$(XSLT) $(HTML_PARAMS) $(XSLT_DIR)/html/docbook.xsl manual.docbook > $(BUILD_DIR)/manual.html

$(BUILD_DIR)/manual.css: manual.css | $(BUILD_DIR)
	cp -v manual.css $(BUILD_DIR)/


pdf: $(BUILD_DIR)/manual.pdf

$(BUILD_DIR)/manual.pdf: $(BUILD_DIR)/manual.fo fop\ config.xml | $(BUILD_DIR)
	$(FOP) -c "fop config.xml" $(BUILD_DIR)/manual.fo $(BUILD_DIR)/manual.pdf

$(BUILD_DIR)/manual.fo: custom-fo.xsl manual.docbook $(MANUAL_DEPENDS) | $(BUILD_DIR)
	$(XSLT) custom-fo.xsl manual.docbook > $(BUILD_DIR)/manual.fo


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
	rm -rv $(BUILD_DIR) $(API_DOCS_DIR)

