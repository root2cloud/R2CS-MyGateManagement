from odoo import models, fields, api

class CommunityPost(models.Model):
    _name = 'community.post'
    _description = 'Community Post'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string="Title", required=True, tracking=True)
    description = fields.Html(string="Content", required=True, sanitize=True)
    image = fields.Binary(string="Image", attachment=True)

    author_id = fields.Many2one(
        'res.users',
        string="Posted By",
        default=lambda self: self.env.user,
        readonly=True
    )

    community_id = fields.Many2one(
        'community.management',
        string="Community",
        required=True
    )

    like_count = fields.Integer(
        string="Likes",
        compute="_compute_like_count",
        store=True
    )

    @api.depends()
    def _compute_like_count(self):
        for post in self:
            post.like_count = self.env['community.post.like'].search_count([
                ('post_id', '=', post.id)
            ])

    view_count = fields.Integer(
        string="Views",
        compute="_compute_view_count",
        store=True
    )

    @api.depends()
    def _compute_view_count(self):
        for post in self:
            post.view_count = self.env['community.post.view'].search_count([
                ('post_id', '=', post.id)
            ])

    comment_count = fields.Integer(
        string="Comments",
        compute="_compute_comment_count",
        store=True
    )

    @api.depends()
    def _compute_comment_count(self):
        for post in self:
            post.comment_count = self.env['community.post.comment'].search_count([
                ('post_id', '=', post.id),
                ('active', '=', True)
            ])

    active = fields.Boolean(default=True)

    image_url = fields.Char(
        string="Image URL",
        compute="_compute_image_url",
        store=False
    )

    def _compute_image_url(self):
        for post in self:
            if post.image:
                try:
                    if isinstance(post.image, bytes):
                        post.image_url = f"data:image/png;base64,{post.image.decode('utf-8')}"
                    else:
                        post.image_url = f"data:image/png;base64,{post.image}"
                except:
                    post.image_url = False
            else:
                post.image_url = False


class CommunityPostLike(models.Model):
    _name = 'community.post.like'
    _description = 'Community Post Like'
    _rec_name = 'post_id'

    _sql_constraints = [
        ('unique_post_user',
         'unique(post_id, user_id)',
         'User can like a post only once!')
    ]

    post_id = fields.Many2one('community.post', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', ondelete='cascade', required=True, default=lambda self: self.env.user)
    create_date = fields.Datetime(default=lambda self: fields.Datetime.now())


class CommunityPostView(models.Model):
    _name = 'community.post.view'
    _description = 'Community Post View'
    _rec_name = 'post_id'

    _sql_constraints = [
        ('unique_post_user_view',
         'unique(post_id, user_id)',
         'User view is already counted for this post!')
    ]

    post_id = fields.Many2one('community.post', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', ondelete='cascade', required=True, default=lambda self: self.env.user)
    view_date = fields.Datetime(default=lambda self: fields.Datetime.now())


class CommunityPostComment(models.Model):
    _name = 'community.post.comment'
    _description = 'Community Post Comment'
    _rec_name = 'post_id'
    _order = 'create_date asc'

    post_id = fields.Many2one('community.post', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', ondelete='cascade', required=True, default=lambda self: self.env.user)
    content = fields.Text(string="Comment", required=True)
    create_date = fields.Datetime(default=lambda self: fields.Datetime.now())
    active = fields.Boolean(default=True)