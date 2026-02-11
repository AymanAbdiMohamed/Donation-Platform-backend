"""
Story Routes.

Charity users can create/manage beneficiary stories.
Public users and donors can view published stories.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth import role_required
from app.extensions import db, limiter
from app.services import CharityService
from app.models import Story
from app.errors import bad_request, not_found

stories_bp = Blueprint("stories", __name__)


# ── Public routes ──────────────────────────────────────────────────

@stories_bp.route("/stories", methods=["GET"])
def get_public_stories():
    """Get all published stories (public access, paginated)."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    charity_id = request.args.get("charity_id", type=int)

    query = Story.query.filter_by(is_published=True)
    if charity_id:
        query = query.filter_by(charity_id=charity_id)

    pagination = query.order_by(Story.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "stories": [s.to_dict() for s in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    }), 200


@stories_bp.route("/stories/<int:story_id>", methods=["GET"])
def get_public_story(story_id):
    """Get a single published story (public access)."""
    story = Story.query.get(story_id)
    if not story or not story.is_published:
        return not_found("Story not found")
    return jsonify({"story": story.to_dict()}), 200


# ── Charity routes (manage own stories) ─────────────────────────

@stories_bp.route("/charity/stories", methods=["GET"])
@role_required("charity")
def get_charity_stories():
    """Get all stories for the authenticated charity."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    stories = Story.query.filter_by(charity_id=charity.id).order_by(
        Story.created_at.desc()
    ).all()

    return jsonify({
        "stories": [s.to_dict() for s in stories]
    }), 200


@stories_bp.route("/charity/stories", methods=["POST"])
@role_required("charity")
@limiter.limit("10 per minute")
def create_story():
    """Create a new beneficiary story."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if not title:
        return bad_request("Title is required")
    if len(title) > 300:
        return bad_request("Title must be 300 characters or fewer")
    if not content:
        return bad_request("Content is required")

    story = Story(
        charity_id=charity.id,
        title=title,
        content=content,
        image_path=data.get("image_path"),
        is_published=data.get("is_published", True),
    )
    db.session.add(story)
    db.session.commit()

    return jsonify({
        "message": "Story created successfully",
        "story": story.to_dict()
    }), 201


@stories_bp.route("/charity/stories/<int:story_id>", methods=["PUT"])
@role_required("charity")
def update_story(story_id):
    """Update an existing story."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    story = Story.query.get(story_id)
    if not story or story.charity_id != charity.id:
        return not_found("Story not found")

    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            return bad_request("Title cannot be empty")
        story.title = title
    if "content" in data:
        content = (data["content"] or "").strip()
        if not content:
            return bad_request("Content cannot be empty")
        story.content = content
    if "image_path" in data:
        story.image_path = data["image_path"]
    if "is_published" in data:
        story.is_published = bool(data["is_published"])

    db.session.commit()

    return jsonify({
        "message": "Story updated successfully",
        "story": story.to_dict()
    }), 200


@stories_bp.route("/charity/stories/<int:story_id>", methods=["DELETE"])
@role_required("charity")
def delete_story(story_id):
    """Delete a story."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    story = Story.query.get(story_id)
    if not story or story.charity_id != charity.id:
        return not_found("Story not found")

    db.session.delete(story)
    db.session.commit()

    return jsonify({"message": "Story deleted"}), 200
