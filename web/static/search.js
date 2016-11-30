function handle_subscription(series_id) {
    $('button[data-series-id=' + series_id + ']').
        text('Unsubscribe').
        addClass('btn-danger').
        removeClass('btn-success');
}

function fail_subscription() {
    alert("An error occurred, preventing your subscription from processing.");
}

function handle_unsubscription(series_id) {
    $('button[data-series-id=' + series_id + ']').
        text('Subscribe').
        addClass('btn-success').
        removeClass('btn-danger');
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
            $.ajax('/unsubscribe', {'success': handle_unsubscription, 'error': fail_unsubscription, 'data': data});
        } else if (this.textContent == "Subscribe") {
            $.ajax('/subscribe', {'success': handle_subscription, 'error': fail_subscription, 'data': data})
        }
    });
});
