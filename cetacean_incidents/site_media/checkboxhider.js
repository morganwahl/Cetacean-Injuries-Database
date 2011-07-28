var CheckboxHider = {
    'init_with_selectors': function(checkbox_name, element_selector) {
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
                $(element_selector).show();
            } else {
                $(element_selector).hide();
            }
        });
        $(checkbox_sel).change();
    }
}
CheckboxHider.init = function(checkbox_name, element_id) {
    CheckboxHider.init_with_selectors(checkbox_name, '#' + element_id);
};
