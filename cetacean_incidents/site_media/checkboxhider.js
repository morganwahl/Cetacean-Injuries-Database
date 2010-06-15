var CheckboxHider = {
    'init': function(checkbox_name, element_id) {
        var checkbox_sel = "[name=" + checkbox_name + "]";
        $(checkbox_sel).change(function(event){
            if ($(this).val() == 'on') {
                $('#' + element_id).show();
            } else if ($(this).val() == '') {
                $('#' + element_id).hide();
            } else {
                alert("unknown val! :" + $(this).val());
            }
        });
        $(checkbox_sel).change();
    }
}

