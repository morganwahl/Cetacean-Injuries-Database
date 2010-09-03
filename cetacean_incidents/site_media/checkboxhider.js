var CheckboxHider = {
    'init': function(checkbox_name, element_id) {
        var checkbox_sel = "[name=" + checkbox_name + "]";
        // This is the hack for IE
        // see http://stackoverflow.com/questions/208471
        if ($.browser.msie) {
          $(checkbox_sel).click(function() {
            this.blur();
            this.focus();
          });
        }
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

