var RadioHider = {
    'init': function(radio_name, val_to_id_map) {
        var radio_sel = "[name=" + radio_name + "]";
        // This is the hack for IE
        // see http://stackoverflow.com/questions/208471
        if ($.browser.msie) {
          $(radio_sel).click(function() {
            this.blur();
            this.focus();
          });
        }
        $(radio_sel).change(function(event){
            for (var val in val_to_id_map) {
                var id = val_to_id_map[val];
                if ($(this).val() == val)
                    $('#' + id).show();
                else
                    $('#' + id).hide();
            }
        });
        $(radio_sel).filter(':checked').change();
    }
}

