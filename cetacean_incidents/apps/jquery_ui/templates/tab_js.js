$('.link-to-{{ tab.html_id }}').click(function() { // bind click event to link
    $tabs.tabs('select', '#{{ tab.html_id }}'); // switch to animal tab
    return false;
});

