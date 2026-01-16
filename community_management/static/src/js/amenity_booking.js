odoo.define('society_amenity_booking.amenity_calendar', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');

    publicWidget.registry.AmenityCalendar = publicWidget.Widget.extend({
        selector: '#calendar-picker',
        start: function () {
            var self = this;
            var bookedDates = JSON.parse(this.$el.data('booked-dates') || '[]');
            var today = new Date().toISOString().split('T')[0];

            // Generate calendar for next 30 days
            var html = '';
            for (var i = 0; i < 42; i++) {
                var date = new Date();
                date.setDate(date.getDate() + i);
                var dateStr = date.toISOString().split('T')[0];
                var dayClass = 'day-cell p-3 border rounded mx-1 d-inline-block cursor-pointer';
                if (dateStr < today) dayClass += ' bg-secondary text-white';
                else if (bookedDates.includes(dateStr)) dayClass += ' bg-dark text-white';
                else dayClass += ' bg-success text-white';
                html += `<div class="${dayClass}" data-date="${dateStr}">${date.getDate()}</div>`;
            }
            this.$el.html(html);

            this.$('.day-cell:not(.bg-secondary):not(.bg-dark)').click(function () {
                $('#selected_date').val($(this).data('date'));
                $('.day-cell').removeClass('bg-warning').addClass('bg-success');
                $(this).removeClass('bg-success').addClass('bg-warning');
            });
        },
    });
});
