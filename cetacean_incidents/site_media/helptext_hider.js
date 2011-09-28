$().ready(function(){
    $('.help_text').before('<a href="" class="help_text_toggle">definition...</a>');
    $('a.help_text_toggle').click(function(){
        $(this).next('.help_text').toggle('fast');
        return false;
    });
});
