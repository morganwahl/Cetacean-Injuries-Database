$().ready(function(){
    $('div.hideable_widget__hider').each(function(){
        var checkboxes = $(this).find('input[type="checkbox"]');
        var checkbox = checkboxes.first();
        var subfield = $(this).next('div.hideable_widget__hidden').find('[id]').first();
        CheckboxHider.init(checkbox.attr('name'), subfield.attr('id'));
    });
});
