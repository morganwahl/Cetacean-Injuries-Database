var RadioHider = {
    'init': function(radio_name, val_to_id_map) {
        var radio_sel = "[name=" + radio_name + "]";
        $(radio_sel).change(function(event){
            for (var val in val_to_id_map) {
                var id = val_to_id_map[val];
                if ($(this).val() == val)
                    $('#' + id).show();
                else
                    $('#' + id).hide();
            }
        });
        $(radio_sel).change();
    }
}

