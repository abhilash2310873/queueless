"""In-app notifications, complaints, the activity log, and saved predictions."""

from app.extensions import db
from app.models.user import utcnow


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", backref="notifications")


class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User")
    stall = db.relationship("Stall")


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    detail = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    actor = db.relationship("User")


class PredictionRecord(db.Model):
    __tablename__ = "prediction_records"

    id = db.Column(db.Integer, primary_key=True)
    stall_id = db.Column(db.Integer, db.ForeignKey("stalls.id"), nullable=False, index=True)
    hour = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(10), nullable=False)
    note = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
