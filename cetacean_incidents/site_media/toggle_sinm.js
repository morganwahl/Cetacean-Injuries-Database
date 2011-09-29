// hook up the SI&M toggle link
// assumes the form is in a table
$().ready(function(){
  var the_fields = $('tr:has(.si_n_m)');
  // initially hide them
  $(the_fields).hide();
  $('.toggle_sinm_link').click(function(event){
    $(the_fields).toggle();
    return false;
  });
});
