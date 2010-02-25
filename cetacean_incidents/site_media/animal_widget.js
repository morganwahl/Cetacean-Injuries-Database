google.load("jquery", "1", {uncompressed: true});

// there's three states to switch between:
//   1. if the chosen_animal is empty and the animal_filter is emtpy,
//      the results_box and the clear_animal button are hidden,
//      and chosen_animal is <i>none chosen</i>
//   2. if chosen_animal is empty and animal_filter isn't, the
//      results_box is visible, clear_animal is hidden and chosen_animal
//      is none
//   3. if chosen_animal isn't empty, animal_filter is disabled,
//      results_box is hidden and clear_animal is shown

// possible state changes:
// no_query->query (1->2)
// query->query (2->2)
// query->chosen (2->3)
// chosen->query (3->2)
// query->no_query (2->1)

function clear_animal() {
    $("[name=animal]").val('');
    $("#animal_chosen").html("<i>none chosen</i>");
    $("#clear_animal").hide();
    $("#animal_filter").removeAttr('disabled');
    check_filter()
}

function check_filter() {
    var query = $("#animal_filter").val();
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
    $("#results_box").html('<img src="/site_media/Loader3.gif"></img> <i>searching</i>'); 
    $("#results_box").show();
    $.getJSON(
        // TODO error-handling!
        // TODO get URL from django?
        "/incidents/animal_search",
        { q: query},
        function(animals){
            // TODO this func is called asynchronously. make
            // sure old results don't overright newer ones.
            if (! animals.length) {
                $("#results_box").html("<i>no animals match</i>");
                return;
            }
            $('#results_box').html('<table id="animal_list"></table>');
            for(var i = 0; i < animals.length; i++) {
                var animal = animals[i];
                var tr_id = 'animal' + animal.id;
                var item = '<tr id="' + tr_id + '"><td class="animal">';
                item += '<div class="animal_name">' + animal.display_name + '</div>';
                item += '<div class="animal_id">' + animal.id + '</div>';
                if (animal.determined_taxon ) {
                    item += '<div class="taxon">' 
                        + animal.determined_taxon 
                        + '</div></td></tr>'
                }
                $("#animal_list").append(item);
                var tr = $("#" + tr_id);
                tr.mouseleave(function (event){
                    $(this).removeClass('highlighted');
                });
                tr.mouseenter(function (event){
                    $(this).addClass('highlighted');
                });
                tr.click(function (event){
                    var animal = {
                        display_name: $(this).find('.animal_name').text(),
                        id: $(this).find('.animal_id').text()
                    }
                    $("#animal_chosen").text(animal.display_name);
                    // TODO get name from django
                    $("[name=animal_field]").val(animal.id);
                    $("#clear_animal").show();
                    // hide the search results and disable the filter
                    $("#results_box").hide();
                    $("#animal_filter").attr('disabled', 'disabled');
                });
            }
        }
    );
}

google.setOnLoadCallback(function() {
    $(document).ready(function() {
        // position the results box under the filter input
        var offset = $("#animal_filter").offset();
        var width = $("#animal_filter").outerWidth();
        var height = $("#animal_filter").outerHeight();
        var left = offset.left;
        var top = offset.top + height;
        $("#results_box").css({
            position: 'absolute',
            top: top,
            left: left
        }).width(width);
        $("#animal_filter").keyup(check_filter);
        check_filter();

        $("#clear_animal").click(clear_animal);
        clear_animal();
    });
});

