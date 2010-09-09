var taxon_autocomplete_source = function (request, response) {
    // request.term has the search term
    // response is a function that takes the results as it's only arg
    
    // TODO no hardcoded URLs
    var query_url = '/taxons/search'
    $.getJSON(
        // TODO error-handling!
        query_url,
        { q: request.term},
        function(taxons) {
            var suggests  = []
            for(var i = 0; i < taxons.length; i++) {
                suggests[i] = {};
                suggests[i].label = taxons[i].display_name;
                suggests[i].value = taxons[i].id;
                suggests[i].common_names = taxons[i].common_names;
            }
            
            response(suggests);
        }
    );
}

var taxon_autocomplete_entry = function(item) {
    var e = '<span class="taxon_name">' + item.label + '</span>'
    if (item.common_names) {
        e += '<span class="common_names">' + item.common_names + '</span>'
    }
    return e
}

