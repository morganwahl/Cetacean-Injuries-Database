// note that this needs to be set before the source is used
var animal_autocomplete_source_url = undefined;

var animal_autocomplete_source = function (request, response) {
    // request.term has the search term
    // response is a function that takes the results as it's only arg
    
    $.getJSON(
        // TODO error-handling!
        animal_autocomplete_source_url,
        { q: request.term},
        function(animals) {
            var suggests  = []
            for(var i = 0; i < animals.length; i++) {
                suggests[i] = {};
                suggests[i].label = animals[i].plain_name;
                suggests[i].html_label = animals[i].html_name;
                suggests[i].id = animals[i].id;
                suggests[i].value = animals[i].id;
                suggests[i].taxon = animals[i].taxon;
            }
            
            response(suggests);
        }
    );
}

function zero_pad(number, size) {
    var integer = number.toFixed(0)
    if (integer.length >= size) {
        return integer;
    } 
    
    var zeros = ''
    for (z = 0; z < size - integer.length; z++) {
        zeros += '0'
    }
    
    return zeros + integer;
}

var animal_autocomplete_entry = function(item) {
    var e = '<span class="animal_display">' + item.html_label + '</span>';
    if (item.taxon) {
        e += '<span class="animal_taxon">' + item.taxon + '</span>';
    }
    e += '<span class="animal_id">#' + zero_pad(item.id, 6) + '</span>';
    return e;
}

