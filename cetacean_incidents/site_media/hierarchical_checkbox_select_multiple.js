$().ready(function(){
    // update 'checked' class
    var UL_CLASS = 'hierarchical_checkbox_select_multiple';
    var ul = $('ul.' + UL_CLASS);
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
    
    // add the expand/contract links
    // TODO remove hard-coded URL
    var minus_url = '/site_media/icons/bullet_toggle_minus.png';
    var minus_img = '<img class="button" title="contract" alt="&#x2212;" src="' + minus_url + '">';
    var plus_url = '/site_media/icons/bullet_toggle_plus.png';
    var plus_img = '<img class="button" title="expand" alt="&#x002b;" src="' + plus_url + '">';
    // only prepend to li that contain sublists
    ul.children('li').has('ul.' + UL_CLASS).prepend('<a href="" class="heir_toggle"></a>');
    ul.find('a.heir_toggle').each(function(){
        function expand(toggle) {
            $(toggle).html(minus_img);
            $(toggle).addClass('expanded');
            $(toggle).nextAll('ul.' + UL_CLASS).show('fast');
        }
        function contract(toggle) {
            $(toggle).removeClass('expanded');
            $(toggle).html(plus_img);
            $(toggle).nextAll('ul.' + UL_CLASS).hide('fast');
        }
        // initialize the non-subchecked LIs to contracted
        if ($(this).closest('li').hasClass('subchecked')) {
            expand(this);
        } else {
            contract(this);
        }
        $(this).click(function(event){
            // 'this' is now the 'a' that was clicked
            if ($(this).hasClass('expanded')) {
                contract(this);
            } else {
                expand(this);
            }
            return false;
        });
    });
});

