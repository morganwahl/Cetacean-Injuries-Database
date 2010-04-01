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

TaxonWidget = {
    init: function (field_name, filter_id, results_id, chosen_id, clear_id) {
        var clear_results = function () {
            $("#" + results_id).hide();
            return;
        }
        
        var taxon_selected = function() {
            $("#" + clear_id).show();
            // hide the search results and disable the filter
            $("#" + results_id).hide();
            $("#" + filter_id).attr('disabled', 'disabled');
        }

        function update_results(query) {
            // start the 'throbber' to show we're waiting on the network
            // TODO get URL from django
            $("#" + results_id).html('<img src="/site_media/Loader3.gif"></img> <i>searching</i>'); 
            $("#" + results_id).show();
            $.getJSON(
                // TODO error-handling!
                // TODO get URL from django
                "/taxons/taxon_search",
                { q: query},
                function(taxons){
                    // position the results box under the filter input
                    var offset = $("#" + filter_id).offset();
                    var width = $("#" + filter_id).outerWidth();
                    var height = $("#" + filter_id).outerHeight();
                    var left = offset.left;
                    var top = offset.top + height;
                    $("#" + results_id).css({
                        position: 'absolute',
                        top: top,
                        left: left
                    }).width(width);

                    // TODO this func is called asynchronously. make
                    // sure old results don't overright newer ones.
                    if (! taxons.length) {
                        $('#' + results_id).html("<i>no taxons match</i>");
                        return;
                    }
                    var table_id = field_name + '_taxon_list';
                    $('#' + results_id).html('<table id="' + table_id + '"></table>');
                    for(var i = 0; i < taxons.length; i++) {
                        var taxon = taxons[i];
                        var tr_id = table_id + '_taxon' + taxon.id;
                        var item = '<tr id="' + tr_id + '"><td class="taxon">';
                        item += '<div class="taxon_name">' + taxon.display_name + '</div>';
                        item += '<div class="taxon_id">' + taxon.id + '</div>';
                        if (taxon.common_names) {
                            item += '<div class="common_names">' + taxon.common_names + '</div></td></tr>'
                        }
                        $("#" + table_id).append(item);
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
                            $("#" + chosen_id).text(taxon.display_name);
                            $("[name=" + field_name + "]").val(taxon.id);
                            taxon_selected();
                        });
                    }
                }
            );
        }

        var check_filter = function () {
            var query = $("#" + filter_id).val();
            if (query == '') {
                clear_results();
            } else {
                update_results(query);
            }
        }

        var clear_taxon = function () {
            $("[name=" + field_name + "]").val('');
            $("#" + chosen_id).html("<i>none chosen</i>");
            $("#" + clear_id).hide();
            $("#" + filter_id).removeAttr('disabled');
            check_filter()
        }


        google.setOnLoadCallback(function() {
            $(document).ready(function() {
                $("#" + filter_id).keyup(check_filter);
                //check_filter();

                $("#" + clear_id).click(clear_taxon);
                //clear_taxon();
                
                if ($("[name=" + field_name + "]").val()) {
                    taxon_selected();
                }
            });
        });
    }
}

