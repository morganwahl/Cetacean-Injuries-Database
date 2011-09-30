FOP := fop -q
XSLT := xsltproc --xinclude

XSLT_DIR := /usr/share/xml/docbook/stylesheet/docbook-xsl

STYLESHEET := manual.css
HTML_PARAMS := --stringparam html.stylesheet $(STYLESHEET)

BUILD_DIR := output

MANUAL_DEPENDS := TRT\ example.html api.docbook model.docbook reports.docbook ui.docbook biologist.docbook

IMAGES := \
	$(BUILD_DIR)/images/1.png \
	$(BUILD_DIR)/images/2.svg \
	$(BUILD_DIR)/images/2.svg.png \
	$(BUILD_DIR)/images/3.png \
	$(BUILD_DIR)/images/4.png \
	$(BUILD_DIR)/images/5.png \
	$(BUILD_DIR)/images/6.png \
	$(BUILD_DIR)/images/7.png \
	$(BUILD_DIR)/images/8.png \
	$(BUILD_DIR)/images/9.png \
	$(BUILD_DIR)/images/10.png \
	$(BUILD_DIR)/images/11.png \
	$(BUILD_DIR)/images/12.png \
	$(BUILD_DIR)/images/13.png \
	$(BUILD_DIR)/images/14.png \
	$(BUILD_DIR)/images/15.png \
	

.PHONEY: all html pdf

all: html pdf

html: $(BUILD_DIR)/manual.html $(BUILD_DIR)/manual.css $(IMAGES)

$(BUILD_DIR)/manual.html: manual.docbook $(MANUAL_DEPENDS) | $(BUILD_DIR)
	$(XSLT) $(HTML_PARAMS) $(XSLT_DIR)/xhtml/docbook.xsl manual.docbook > $(BUILD_DIR)/manual.html

$(BUILD_DIR)/manual.css: manual.css | $(BUILD_DIR)
	cp -v manual.css $(BUILD_DIR)/

$(BUILD_DIR)/images/%: images/% | $(BUILD_DIR)/images
	cp -v $< $@

$(BUILD_DIR)/images: | $(BUILD_DIR)
	mkdir $(BUILD_DIR)/images

# 2.svg uses 2.png
$(BUILD_DIR)/images/2.svg: $(BUILD_DIR)/images/2.png

pdf: $(BUILD_DIR)/manual.pdf

$(BUILD_DIR)/manual.pdf: $(BUILD_DIR)/manual.fo fop\ config.xml $(IMAGES) | $(BUILD_DIR)
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
$(API_DOCS_DIR)/%.docbook: $(PROJECT_DIR)/cetacean_incidents/apps/describe_fields/management/commands/document_fields.py $(PROJECT_DIR)/cetacean_incidents/settings.py $(PROJECT_DIR)/cetacean_incidents/local_settings.py | $(API_DOCS_DIR)
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
