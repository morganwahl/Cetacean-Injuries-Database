$().ready(function(){
    var widgets = $('form span.match_widget');
    widgets.each(function(index, elem){
        var lookup = $(elem).find('span.lookup select').first();
        lookup.change(function(event){
            var val = $(this).val();
            var relevant = $(elem).find('span.' + val + '_value');
            var others = $(elem).find('span.value').not(relevant);
            // hide all the other values
            others.hide();
            // disable the other values
            others.find('[name]').attr("disabled", "disabled");
            // if val isn't blank
            if (val != '') {
                // enable the relevant value
                relevant.find('[name]').removeAttr("disabled");
                // show the relevant value
                relevant.show();
            }
        });
        // trigger the event to be sure the correct field is displayed for the
        // initial value
        lookup.change();
    });
});
