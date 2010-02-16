google.load("jquery", "1", {uncompressed: true});

// there's three states to switch between:
//   1. if the chosen_taxon is empty and the taxon_filter is emtpy,
//      the results_box and the clear_taxon button are hidden,
//      and chosen_taxon is <i>none chosen</i>
//   2. if chosen_taxon is empty and taxon_filter isn't, the
//      results_box is visible, clear_taxon is hidden and chosen_taxon
//      is none
//   3. if chosen_taxon isn't empty, taxon_filter is disabled,
//      results_box is hidden and clear_taxon is shown

// possible state changes:
// no_query->query (1->2)
// query->query (2->2)
// query->chosen (2->3)
// chosen->query (3->2)
// query->no_query (2->1)

function clear_taxon() {
    $("[name=taxon]").val('');
    $("#taxon_chosen").html("<i>none chosen</i>");
    $("#clear_taxon").hide();
    $("#taxon_filter").removeAttr('disabled');
    check_filter()
}

function check_filter() {
    var query = $("#taxon_filter").val();
    if (query == '') {
        clear_results();
    } else {
        update_results(query);
    }
}

function clear_results() {
    $("#results_box").hide();
    return;
}

function update_results(query) {
    // start the 'throbber' to show we're waiting on the network
    $("#results_box").html('<img src="/site_media//Loader3.gif"></img> <i>searching</i>'); 
    $("#results_box").show();
    $.getJSON(
        // TODO error-handling!
        // TODO get URL from django?
        "/taxons/taxon_search",
        { q: query},
        function(taxons){
            // TODO this func is called asynchronously. make
            // sure old results don't overright newer ones.
            if (! taxons.length) {
                $("#results_box").html("<i>no taxons match</i>");
                return;
            }
            $('#results_box').html('<table id="taxon_list"></table>');
            for(var i = 0; i < taxons.length; i++) {
                var taxon = taxons[i];
                var tr_id = 'taxon' + taxon.id;
                var item = '<tr id="' + tr_id + '"><td class="taxon">';
                item += '<div class="taxon_name">' + taxon.display_name + '</div>';
                item += '<div class="taxon_id">' + taxon.id + '</div>';
                if (taxon.common_name) {
                    item += '<div class="common_name">' + taxon.common_name + '</div></td></tr>'
                }
                $("#taxon_list").append(item);
                var tr = $("#" + tr_id);
                tr.mouseleave(function (event){
                    $(this).removeClass('highlighted');
                });
                tr.mouseenter(function (event){
                    $(this).addClass('highlighted');
                });
                tr.click(function (event){
                    var taxon = {
                        display_name: $(this).find('.taxon_name').text(),
                        id: $(this).find('.taxon_id').text()
                    }
                    $("#taxon_chosen").text(taxon.display_name);
                    $("[name=taxon]").val(taxon.id);
                    $("#clear_taxon").show();
                    // hide the search results and disable the filter
                    $("#results_box").hide();
                    $("#taxon_filter").attr('disabled', 'disabled');
                });
            }
        }
    );
}

google.setOnLoadCallback(function() {
    $(document).ready(function() {
        // position the results box under the filter input
        var offset = $("#taxon_filter").offset();
        var width = $("#taxon_filter").outerWidth();
        var height = $("#taxon_filter").outerHeight();
        var left = offset.left;
        var top = offset.top + height;
        $("#results_box").css({
            position: 'absolute',
            top: top,
            left: left
        }).width(width);
        $("#taxon_filter").keyup(check_filter);
        check_filter();

        $("#clear_taxon").click(clear_taxon);
        clear_taxon();
    });
});

