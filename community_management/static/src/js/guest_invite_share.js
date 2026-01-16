// static/src/js/guest_invite_share.js
odoo.define('community_management.guest_invite_share', function (require) {
    'use strict';

    window.shareGuestInvite = function (button) {
        var text = button.getAttribute('data-share-text') || '';
        if (navigator.share) {
            navigator.share({ text: text }).catch(function (err) {
                console.error('Share failed', err);
                alert('Sharing is not available on this device.');
            });
        } else if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(function () {
                alert('Invite text copied. Paste it in WhatsApp or any app to share.');
            }).catch(function () {
                alert('Sharing is not supported in this browser.');
            });
        } else {
            alert('Sharing is not supported in this browser.');
        }
    };
});
