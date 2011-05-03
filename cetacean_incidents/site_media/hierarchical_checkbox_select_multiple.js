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
            li.find('li').addClass('superchecked');
        } else {
            var still_superchecked = ul.find('li.checked').find('li');
            li.find('li').not(still_superchecked).removeClass('superchecked');
        }
        
        if (this.checked) {
            // add 'subchecked' class to all parent items that aren't children
            // of a checked item
            var checked_or_superchecked = ul.find('li.checked').add('li.superchecked');
            ul.find('li').has(this).not(checked_or_superchecked).addClass('subchecked');
        } else {
            // removed 'subchecked' class from parents that don't still contain
            // a checked input
            var still_subchecked = ul.find('li').has('input:checkbox:checked');
            ul.find('li').has(this).not(still_subchecked).removeClass('subchecked');
        }
    });
        }
    });
});

