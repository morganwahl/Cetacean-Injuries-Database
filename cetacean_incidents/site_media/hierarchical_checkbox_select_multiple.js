$().ready(function(){
    // update 'checked' class
    var ul = $('ul.hierarchical_checkbox_select_multiple');
    ul.children('li').find('input:checkbox').change(function(event){
        // 'this' is the checkbox
        // 'li' is the LI that contains the checkbox
        var li = $(this).closest('li');
        if (this.checked) {
            li.addClass('checked');
        } else {
            li.removeClass('checked');
        }
        
        if (this.checked) {
            // add 'subchecked' class to all parent items
            ul.find('li').has(this).addClass('subchecked');
        } else {
            // removed 'subchecked' class from parents that don't still contain
            // a checked input
            var still_checked = ul.find('li').has('input:checkbox:checked');
            ul.find('li').has(this).not(still_checked).removeClass('subchecked');
        }
    });
});

