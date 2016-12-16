$(function() {
    jQuery.extend( jQuery.fn.dataTableExt.oSort, {
        "title-pre": function ( a ) {
            return a.replace(/\b(an?|the) /gi, "");
        },

        "title-asc": function ( a, b ) {
            return ((a < b) ? -1 : ((a > b) ? 1 : 0));
        },

        "title-desc": function ( a, b ) {
            return ((a < b) ? 1 : ((a > b) ? -1 : 0));
        }
    } );

    $('table input[type=checkbox]').bootstrapToggle();
    $('tr input,select').change(function() {
        var row = $(this).parents('tr');
        var data = {
            'enabled': row.find('[name=enabled]').is(':checked') + 0,
            'shift_len': parseInt(row.find('[name=shift_len]').val()),
            'shift_type': row.find('[name=shift_type]').val(),
            'subscription_id': parseInt(row.attr('data-subscription-id')),
        }
        if (!isNaN(data['shift_len'])) {
            $.ajax({
                url: "/update_subscription",
                data: data,
                error: function() { alert("Update failed"); },
            })
        }
    });

    $('#subscriptions').dataTable({
        columnDefs: [
            {'type': 'title', 'targets': 0},
            {'orderable': false, 'searchable': false, 'targets': [2, 3, 4]}
        ]
    });
});
