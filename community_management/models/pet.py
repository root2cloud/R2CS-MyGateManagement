from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class Pet(models.Model):
    _name = 'pet.management'
    _description = 'Pet Management'
    _rec_name = 'name'

    # Tenant and Flat Information
    tenant_id = fields.Many2one('res.partner', string='Owner (Tenant)', required=True)
    flat_id = fields.Many2one('flat.management', string='Flat', compute='_compute_flat_id', store=True)
    building_id = fields.Many2one('building.management', string='Building', compute='_compute_building_id', store=True)

    # Pet Information
    name = fields.Char(string='Pet Name', required=True)
    photo = fields.Image(string='Photo', max_width=200, max_height=200)
    pet_type = fields.Selection([
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('bird', 'Bird'),
        ('rabbit', 'Rabbit'),
        ('fish', 'Fish'),
        ('other', 'Other')
    ], string='Pet Type', required=True, default='dog')

    breed = fields.Char(string='Breed')
    color = fields.Char(string='Color')

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender')

    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age (Years)', compute='_compute_age', store=True)
    weight = fields.Float(string='Weight (kg)')

    # Identification
    microchip_number = fields.Char(string='Microchip Number')
    license_number = fields.Char(string='License Number')

    # Vaccination Status - Auto-computed based on dates
    vaccination_status = fields.Selection([
        ('up_to_date', 'Up to Date'),
        ('due_soon', 'Due Soon'),
        ('overdue', 'Overdue'),
        ('not_vaccinated', 'Not Vaccinated')
    ], string='Vaccination Status',
        compute='_compute_vaccination_status',
        store=True, default='not_vaccinated')

    last_vaccination_date = fields.Date(string='Last Vaccination Date')
    next_vaccination_date = fields.Date(string='Next Vaccination Date')
    days_until_vaccination = fields.Integer(string='Days Until Next Vaccination',
                                            compute='_compute_vaccination_status',
                                            store=True)
    vaccination_ids = fields.One2many('pet.vaccination', 'pet_id', string='Vaccination Records')

    # Health Information
    veterinarian = fields.Char(string='Veterinarian Name')
    vet_phone = fields.Char(string='Veterinarian Phone')
    medical_conditions = fields.Text(string='Medical Conditions')
    allergies = fields.Text(string='Allergies')

    # Additional Information
    special_needs = fields.Text(string='Special Needs')
    notes = fields.Text(string='Additional Notes')

    active = fields.Boolean(string='Active', default=True)

    @api.depends('tenant_id')
    def _compute_flat_id(self):
        """Get flat from tenant's current lease"""
        for record in self:
            flat = self.env['flat.management'].search([
                ('tenant_id', '=', record.tenant_id.id)
            ], limit=1)
            record.flat_id = flat.id if flat else False

    @api.depends('flat_id')
    def _compute_building_id(self):
        """Get building from flat"""
        for record in self:
            if record.flat_id and record.flat_id.building_id:
                record.building_id = record.flat_id.building_id.id
            else:
                record.building_id = False

    @api.depends('date_of_birth')
    def _compute_age(self):
        """Calculate age from date of birth"""
        for record in self:
            if record.date_of_birth:
                today = date.today()
                dob = fields.Date.from_string(record.date_of_birth)
                record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                record.age = 0

    @api.depends('next_vaccination_date', 'last_vaccination_date')
    def _compute_vaccination_status(self):
        """Auto-compute vaccination status based on dates"""
        for record in self:
            today = date.today()

            # If no vaccination dates set
            if not record.next_vaccination_date and not record.last_vaccination_date:
                record.vaccination_status = 'not_vaccinated'
                record.days_until_vaccination = 0
                continue

            # If next vaccination date is set
            if record.next_vaccination_date:
                next_date = fields.Date.from_string(record.next_vaccination_date)
                days_diff = (next_date - today).days
                record.days_until_vaccination = days_diff

                # Overdue (past due date)
                if days_diff < 0:
                    record.vaccination_status = 'overdue'
                # Due soon (within 30 days)
                elif days_diff <= 30:
                    record.vaccination_status = 'due_soon'
                # Up to date (more than 30 days away)
                else:
                    record.vaccination_status = 'up_to_date'
            else:
                record.days_until_vaccination = 0
                record.vaccination_status = 'not_vaccinated'

    @api.model
    def default_get(self, fields_list):
        """Set default tenant_id for portal users"""
        res = super(Pet, self).default_get(fields_list)
        if self.env.user.has_group('base.group_portal'):
            res['tenant_id'] = self.env.user.partner_id.id
        return res

    @api.model
    def _cron_update_vaccination_status(self):
        """Cron job to update vaccination status daily"""
        pets = self.search([('active', '=', True)])
        for pet in pets:
            pet._compute_vaccination_status()


class PetVaccination(models.Model):
    _name = 'pet.vaccination'
    _description = 'Pet Vaccination Record'
    _order = 'vaccination_date desc'

    pet_id = fields.Many2one('pet.management', string='Pet', required=True, ondelete='cascade')
    vaccine_name = fields.Char(string='Vaccine Name', required=True)
    vaccination_date = fields.Date(string='Vaccination Date', required=True, default=fields.Date.today)
    next_due_date = fields.Date(string='Next Due Date')
    veterinarian = fields.Char(string='Veterinarian')
    batch_number = fields.Char(string='Batch Number')
    certificate = fields.Binary(string='Certificate')
    certificate_filename = fields.Char(string='Certificate Filename')
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        """Auto-update pet's vaccination dates when new record added"""
        record = super(PetVaccination, self).create(vals)
        if record.pet_id:
            # Update last vaccination date to most recent
            record.pet_id.last_vaccination_date = record.vaccination_date
            # Update next vaccination date if provided
            if record.next_due_date:
                record.pet_id.next_vaccination_date = record.next_due_date
        return record
