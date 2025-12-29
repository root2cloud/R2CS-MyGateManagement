{
    'name': 'Community Management',
    'version': '1.0',
    'summary': 'Community, building, flat and room management for MyGate project',
    'author': 'Regonda Soujanya',
    'category': 'Community',
    'application': True,
    'depends': ['base', 'web', 'website', 'portal', 'account', 'mail', 'contacts'],
    # Added website dependency for portal features
    'data': [
        'security/ir.model.access.csv',
        'security/family_member_security.xml',
        'security/vehicle_security.xml',
        'security/amenity_security.xml',
        'security/security.xml',
        'security/security_groups.xml',
        'data/pet_cron.xml',
        'security/pet_security.xml',
        'views/community_views.xml',
        'views/building_views.xml',
        'views/flat_views.xml',
        'views/portal_family_member_template.xml',
        'views/pet_views.xml',
        'views/portal_pet_template.xml',
        'views/portal_vehicle_template.xml',
        'views/inquiry_form_template.xml',
        'views/customer_inquiry_views.xml',
        'views/floor_views.xml',
        'views/flat_transaction_views.xml',
        'views/family_member_views.xml',
        'views/vehicle_views.xml',
        'reports/lease_agreement_report.xml',
        'views/maintenance_views.xml',

        # 'views/custom_helpdesk_team_views.xml',
        # 'views/portal_templates.xml',
        'views/notice_board_views.xml',
        'views/portal_notice_board_templates.xml',
        'views/amenity_views.xml',
        'views/portal_profile_overview.xml',

        # not completed below one
        # 'views/amenity_portal_templates.xml',
        'views/demo_template.xml',
        'views/community_lead_views.xml',
        'views/community_dashboard_kanban.xml',

        'views/parking_views.xml',
        'views/resident_access_request_views.xml',
        'views/portal_access_templates.xml',
        'views/festival_views.xml',

        'views/res_partner_views.xml',
        'views/portal_daily_slots_template.xml',
        'views/guest_invite_views.xml',
        'views/portal_guest_invite_templates.xml',
        'views/party_group_invite_views.xml',
        'views/portal_party_group_invite_templates.xml',
        'views/cab_preapproval_views.xml',
        'views/portal_cab_preapproval_templates.xml',
        'data/cab_preapproval_cron.xml',
        'views/delivery_pass_views.xml',
        'views/portal_delivery_pass_templates.xml',
        'views/portal_security_guard_templates.xml',

        # 'views/assets.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'community_management/static/src/sound/notification.mp3',  # Ee line add chey
        ],
    },

    # 'assets': {
    #     'web.assets_frontend': [
    #         'community_management/static/src/js/portal_access_dropdowns.js',
    #     ],
    # },
    'installable': True,
    'auto_install': False,
    'description': 'Custom module for MyGate community management system.',
}
