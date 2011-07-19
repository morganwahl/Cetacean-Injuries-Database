// When a form with a GET method is submitted, disables all the fields with
// empty values in order to shorten the resulting URL.
$().ready(function(){
    // note! assumes lowercase value
    $('form[method="get"]').submit(function(){
        $(this).find('input, select, textarea').filter(':enabled').each(function(){
            if ($(this).val() == '') {
                $(this).attr('disabled', 'disabled');
            }
        });
    });
});
