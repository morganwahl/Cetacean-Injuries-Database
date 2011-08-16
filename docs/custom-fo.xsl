<?xml version="1.0"?>
<xsl:stylesheet 
     xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
     xmlns:fo="http://www.w3.org/1999/XSL/Format"
     xmlns:d="http://docbook.org/ns/docbook" 
     exclude-result-prefixes="d" 
     version="1.0">

<xsl:import href="file:///usr/share/xml/docbook/stylesheet/docbook-xsl/fo/docbook.xsl"/>  

<xsl:param name="paper.type" select="'USletter'"/>

<xsl:attribute-set name="informalexample.properties">
  <xsl:attribute name="keep-together.within-column">always</xsl:attribute>
  <xsl:attribute name="border">0.5pt solid #888</xsl:attribute>
  <xsl:attribute name="padding">.5em</xsl:attribute>
  <xsl:attribute name="background-color">#eee</xsl:attribute>
</xsl:attribute-set>

</xsl:stylesheet>

