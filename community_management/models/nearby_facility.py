from odoo import models, fields

class NearbyFacility(models.Model):
    _name = 'nearby.facility'
    _description = 'Nearby Facilities'

    community_id = fields.Many2one('community.management', string='Community', required=True, ondelete='cascade')
    name = fields.Char(string='Facility Name', required=True)
    facility_type = fields.Selection([
        ('school', 'School'),
        ('college', 'College'),
        ('hospital', 'Hospital'),
        ('restaurant', 'Restaurant'),
        ('temple', 'Temple'),
        ('mosque', 'Mosque'),
        ('church', 'Church'),
        ('mall', 'Shopping Mall'),
        ('supermarket', 'Supermarket'),
        ('bank', 'Bank'),
        ('atm', 'ATM'),
        ('pharmacy', 'Pharmacy'),
        ('gym', 'Gym'),
        ('park', 'Park'),
        ('bus_stand', 'Bus Stand'),
        ('metro', 'Metro Station'),
        ('railway', 'Railway Station'),
        ('airport', 'Airport'),
        ('police', 'Police Station'),
        ('fire', 'Fire Station'),
        ('post_office', 'Post Office'),
        ('other', 'Other')
    ], string='Facility Type', required=True)
    distance = fields.Float(string='Distance (km)')
    description = fields.Text(string='Description')
    facility_image = fields.Image(string='Facility Image')
