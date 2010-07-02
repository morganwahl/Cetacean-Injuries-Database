var CheckboxHider = {
    'init': function(checkbox_name, element_id) {
        var checkbox_sel = "[name=" + checkbox_name + "]";
        $(checkbox_sel).change(function(event){
            if ($(this).attr("checked")) {
                $('#' + element_id).show();
            } else {
                $('#' + element_id).hide();
            }
        });
        $(checkbox_sel).change();
    }
}

