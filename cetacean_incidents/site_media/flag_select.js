var FlagSelect = {
    'init': function(div_id, media_url) {
        var select = $("#" + div_id + " > select");
        select.change(function(event){
            // remove the old flag first
            $("#" + div_id + " > img.flag").remove()
            if ( select.val() == '' )
                return;
            var icon_url = media_url + "flags/" + select.val().toLowerCase()  + ".png";
            $("#" + div_id).prepend('<img class="flag" src="' + icon_url + '">');
        });
        // trigger the event to load the flag for the initial value.
        select.change();
    }
}

