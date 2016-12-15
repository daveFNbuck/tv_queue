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

    $('.series-form').submit(function(e) {
        $.ajax({
            url: "/update_subscription",
            data: $(this).serialize(),
            error: function() { alert("Update failed"); },
        });
        e.preventDefault();
    });

    $('tr input,select').change(function() {
        $.ajax({
            url: "/update_subscription",
            data: $(this).parents('tr').find('form').serialize(),
            error: function() { alert("Update failed"); },
        })
    });

    $('#subscriptions').dataTable({
        columnDefs: [
            {'type': 'title', 'targets': 0},
            {'orderable': false, 'searchable': false, 'targets': [2, 3, 4]}
        ]
    });
});
