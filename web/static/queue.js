function deleteUntil(episode_id) {
    $('#ep_' + episode_id).parents('.panel').prevAll().remove();
    deleteCur(episode_id);
}

function deleteCur(episode_id) {
    var container = $('#ep_' + episode_id).parents('.episodes');
    $('#ep_' + episode_id).parents('.panel').remove();
    var numItems = container.children('.panel').size();
    container.prev().children('span.badge').text(numItems);
    container.find('.panel-footer').first().children('button.watch-until').remove();
    if (numItems === 0) {
        container.parents('.series').remove();
    } else if (numItems === 1) {
        container.parents('.series').find('.episode-label').text('episode');
    }
    $('.navbar .num-queued').text($('.episode').size());
}

function failDelete(item) {
    alert('Failed to communicate with server. Please try again later.');
}

$(function() {
    $('[data-collapse]').click(function() {
        var ep = this.attributes['data-collapse'].value;
        $('#' + ep).collapse('toggle');
    });

    $('button.watch').click(function() {
        var data = {'episode_id': this.attributes['data-episode'].value}
        $.ajax('/watch', {'success': deleteCur, 'error': failDelete, 'data': data});
    });

    $('button.watch-until').click(function() {
        var data = {'episode_id': this.attributes['data-episode'].value}
        $.ajax('/watchuntil', {'success': deleteUntil, 'error': failDelete, 'data': data});
    });
});
