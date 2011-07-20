$().ready(function(){
    $('span.help_text').before('<a href="" class="help_text_toggle">definition...</a>');
    $('a.help_text_toggle').click(function(){
        $(this).next('span.help_text').toggle();
        return false;
    });
    $('span.help_text').hide();
});
