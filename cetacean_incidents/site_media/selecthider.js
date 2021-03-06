var SelectHider = {
    'init': function(select_name, val_to_id_map) {
        var select_sel = "[name=" + select_name + "]";
        $(select_sel).change(function(event){
            // multiple values can be used to show the same ID
            var shown_ids = {}
            for (var val in val_to_id_map) {
                var id = val_to_id_map[val];
                if ($(this).val() == val) {
                    $('#' + id).show();
                    shown_ids[id] = true;
                } else {
                    if (! shown_ids[id])
                        $('#' + id).hide();
                }
            }
        });
        $(select_sel).change();
    }
}

