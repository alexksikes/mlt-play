/* mlt options */
$('#toggle_mlt_params').click(function() {
  $(this).toggleClass('open');
  $('.mlt_params').toggle( 'fast');
});
/* mlt options */

/* more less */
function addMoreLess() {
    $('.toggle_more').click(function () {
        $(this).hide();
        $(this).nextAll('.more_less').css({display:'inline'});
        $(this).siblings('.toggle_less').css({display:'inline'});
    });

    $('.toggle_less').click(function () {
        $(this).hide();
        $(this).prevAll('.more_less').hide();
        $(this).siblings('.toggle_more').css({display:'inline'});
    });
}
addMoreLess();
/* more less */
