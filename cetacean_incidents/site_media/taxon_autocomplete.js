// note that this needs to be set before the source is used
var taxon_autocomplete_source_url = undefined;

var taxon_autocomplete_source = function (request, response) {
    // request.term has the search term
    // response is a function that takes the results as it's only arg
    
    $.getJSON(
        // TODO error-handling!
        taxon_autocomplete_source_url,
        { q: request.term},
        function(taxa) {
            var suggests  = []
            for(var i = 0; i < taxa.length; i++) {
                suggests[i] = {};
                suggests[i].label = taxa[i].plain_name;
                suggests[i].html_label = taxa[i].html_name;
                suggests[i].value = taxa[i].id;
                suggests[i].common_names = taxa[i].common_names;
            }
            
            response(suggests);
        }
    );
}

var taxon_autocomplete_entry = function(item) {
    var e = '<span class="taxon_name">' + item.html_label + '</span>'
    if (item.common_names) {
        e += '<span class="common_names">' + item.common_names + '</span>'
    }
    return e
}

