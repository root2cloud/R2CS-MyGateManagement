from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound
import base64
import json


class CommunityPortalController(http.Controller):

    @http.route(['/community/posts', '/community/posts/page/<int:page>'],
                type='http', auth="user", website=True)
    def community_posts(self, page=1, community_id=None, **kwargs):
        """Display community posts in portal"""
        user = request.env.user

        Post = request.env['community.post'].sudo()
        domain = [('active', '=', True)]

        if community_id:
            domain.append(('community_id', '=', int(community_id)))

        # Pagination
        posts_per_page = 12
        total_posts = Post.search_count(domain)
        pager = request.website.pager(
            url='/community/posts',
            total=total_posts,
            page=page,
            step=posts_per_page,
            scope=5,
            url_args=kwargs
        )

        posts = Post.search(
            domain,
            limit=posts_per_page,
            offset=(page - 1) * posts_per_page,
            order='create_date desc'
        )

        # Get communities for filter
        communities = request.env['community.management'].sudo().search([])

        # Check if user has liked posts
        liked_post_ids = []
        if posts:
            likes = request.env['community.post.like'].sudo().search([
                ('post_id', 'in', posts.ids),
                ('user_id', '=', user.id)
            ])
            liked_post_ids = likes.mapped('post_id.id')

        values = {
            'posts': posts,
            'pager': pager,
            'communities': communities,
            'liked_post_ids': liked_post_ids,
            'current_community_id': community_id,
            'user': user,
        }

        return request.render("community_management.community_posts_template", values)

    @http.route('/community/post/<int:post_id>', type='http', auth="user", website=True)
    def community_post_detail(self, post_id, **kwargs):
        """Display single post detail"""
        user = request.env.user

        post = request.env['community.post'].sudo().browse(post_id)
        if not post.exists() or not post.active:
            raise NotFound()

        # Record view (only once per user)
        View = request.env['community.post.view'].sudo()
        existing_view = View.search([
            ('post_id', '=', post.id),
            ('user_id', '=', user.id)
        ], limit=1)

        if not existing_view:
            View.create({
                'post_id': post.id,
                'user_id': user.id,
            })
            # Force recompute of view_count
            post._compute_view_count()

        # Check if current user liked this post
        is_liked = bool(request.env['community.post.like'].sudo().search([
            ('post_id', '=', post.id),
            ('user_id', '=', user.id)
        ], limit=1))

        # Get recent posts from same community
        recent_posts = request.env['community.post'].sudo().search([
            ('community_id', '=', post.community_id.id),
            ('id', '!=', post.id),
            ('active', '=', True)
        ], limit=5, order='create_date desc')

        # Get comments for this post
        comments = request.env['community.post.comment'].sudo().search([
            ('post_id', '=', post.id),
            ('active', '=', True)
        ], order='create_date asc')

        # Check if current user is the author of this post
        is_author = (post.author_id.id == user.id)

        values = {
            'post': post,
            'is_liked': is_liked,
            'recent_posts': recent_posts,
            'comments': comments,
            'user': user,
            'is_author': is_author,
        }

        return request.render("community_management.community_post_detail_template", values)

    @http.route('/community/post/like', type='json', auth="user")
    def like_post(self, post_id, **kwargs):
        """Like/Unlike a post via AJAX"""
        user = request.env.user

        post = request.env['community.post'].sudo().browse(post_id)
        if not post.exists() or not post.active:
            return {'success': False, 'error': 'Post not found'}

        Like = request.env['community.post.like'].sudo()

        existing_like = Like.search([
            ('post_id', '=', post_id),
            ('user_id', '=', user.id)
        ])

        if existing_like:
            # Unlike
            existing_like.unlink()
            action = 'unliked'
        else:
            # Like
            Like.create({
                'post_id': post_id,
                'user_id': user.id
            })
            action = 'liked'

        # Force recompute of like_count
        post._compute_like_count()

        return {
            'action': action,
            'like_count': post.like_count,
            'success': True
        }

    @http.route('/community/comment/add', type='json', auth="user")
    def add_comment(self, post_id, content, **kwargs):
        """Add a comment via AJAX"""
        user = request.env.user

        post = request.env['community.post'].sudo().browse(post_id)
        if not post.exists() or not post.active:
            return {'success': False, 'error': 'Post not found'}

        if not content or not content.strip():
            return {'success': False, 'error': 'Comment cannot be empty'}

        Comment = request.env['community.post.comment'].sudo()
        comment = Comment.create({
            'post_id': post_id,
            'user_id': user.id,
            'content': content.strip()
        })

        # Force recompute of comment_count
        post._compute_comment_count()

        return {
            'success': True,
            'comment_count': post.comment_count,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user_name': user.name,
                'create_date': comment.create_date.strftime('%b %d, %Y %I:%M %p') if comment.create_date else '',
                'user_id': user.id
            }
        }

    @http.route('/community/comment/delete', type='json', auth="user")
    def delete_comment(self, comment_id, **kwargs):
        """Delete a comment via AJAX"""
        user = request.env.user

        comment = request.env['community.post.comment'].sudo().browse(comment_id)
        if not comment.exists():
            return {'success': False, 'error': 'Comment not found'}

        # Check if user owns the comment
        if comment.user_id.id != user.id:
            return {'success': False, 'error': 'You can only delete your own comments'}

        post = comment.post_id

        # Archive the comment
        comment.write({'active': False})

        # Force recompute of comment_count
        post._compute_comment_count()

        return {
            'success': True,
            'comment_count': post.comment_count
        }

    @http.route('/community/post/create', type='http', auth="user", website=True)
    def create_post(self, **kwargs):
        """Show create post form"""
        communities = request.env['community.management'].sudo().search([])

        values = {
            'communities': communities,
            'user': request.env.user,
        }

        return request.render("community_management.create_post_template", values)

    @http.route('/community/post/submit',
                type='http', auth="user", website=True, methods=['POST'])
    def submit_post(self, **post_data):
        """Submit new post"""
        Post = request.env['community.post'].sudo()

        if not post_data.get('name') or not post_data.get('description'):
            return request.redirect('/community/post/create?error=1')

        post_vals = {
            'name': post_data.get('name'),
            'description': post_data.get('description'),
            'community_id': int(post_data.get('community_id')),
            'author_id': request.env.user.id,
        }

        # Handle image upload
        if 'image' in request.httprequest.files:
            image_file = request.httprequest.files['image']
            if image_file and image_file.filename:
                image_data = image_file.read()
                if image_data:
                    post_vals['image'] = base64.b64encode(image_data)

        # Create post
        post = Post.create(post_vals)

        # Automatically record creator's view
        request.env['community.post.view'].sudo().create({
            'post_id': post.id,
            'user_id': request.env.user.id,
        })

        return request.redirect(f'/community/post/{post.id}')

    @http.route('/community/post/delete/<int:post_id>', type='http', auth="user", website=True)
    def delete_post(self, post_id, **kwargs):
        """Delete post"""
        user = request.env.user
        post = request.env['community.post'].sudo().browse(post_id)

        if not post.exists() or post.author_id.id != user.id:
            raise NotFound()

        # Archive the post
        post.write({'active': False})

        return request.redirect('/community/posts')