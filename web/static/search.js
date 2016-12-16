function handle_subscription(series_id) {
    $('button[data-series-id=' + series_id + ']').
        text('Unsubscribe').
        addClass('btn-danger').
        removeClass('btn-success').
        removeClass('disabled');
}

function fail_subscription() {
    alert("An error occurred, preventing your subscription from processing.");
}

function handle_unsubscription(series_id) {
    $('button[data-series-id=' + series_id + ']').
        text('Subscribe').
        addClass('btn-success').
        removeClass('btn-danger').
        removeClass('disabled');
}

function fail_unsubscription() {
    alert("An error occurred, preventing your unsubscription from processing.");
}

$(function() {
    $('img').error(function() {
        $(this).parents('.episodeBanner').addClass('hidden');
        $(this).parents('.episodeBanner').siblings('.episodeTitle').removeClass('hidden');
    });

    $('button.subscription').click(function() {
        var series_id = this.attributes['data-series-id'].nodeValue;
        var data = {'series_id': series_id}
        if (this.textContent == "Unsubscribe") {
            $('.modal[for_series=' + series_id + ']').modal()
        } else if (this.textContent == "Subscribe") {
            $.ajax('/subscribe', {'success': handle_subscription, 'error': fail_subscription, 'data': data})
        }
    });

    $('.modal.unsubscribe .btn-danger').click(function() {
        var series_id = this.attributes['data-series-id'].nodeValue;
        var data = {'series_id': series_id};
        $.ajax('/unsubscribe', {'success': handle_unsubscription, 'error': fail_unsubscription, 'data': data});
        $('.modal').modal('hide');
    });
});
