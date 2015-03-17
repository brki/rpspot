// Foundation JavaScript
// Documentation can be found at: http://foundation.zurb.com/docs
$(document).foundation();
$(function() {
    $( "#id_start_time" ).datetimepicker({
        dateFormat: 'yy-mm-dd',
        maxDate: 1, // tomorrow
        timeFormat: 'HH:mm',
        showSecond: false
    });
});
