$().ready(function(){
    $('.geartarget_def_toggle').click(function(event){
        $(this).next('.geartarget_def').toggle();
        return false;
    });
});
