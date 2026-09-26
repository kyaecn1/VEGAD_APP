from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    photo = db.Column(db.String(200), default='default.png')
    role = db.Column(db.String(20), default='member')
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class Community(db.Model):
    __tablename__ = 'communities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    safety_score = db.Column(db.Float, default=7.0)
    color_code = db.Column(db.String(7), default='#4CAF50')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    plan = db.Column(db.String(20), default='trial')
    trial_start = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=17))
    subscription_start = db.Column(db.DateTime)
    subscription_end = db.Column(db.DateTime)
    is_subscribed = db.Column(db.Boolean, default=False)

    members = db.relationship('User', backref='community', lazy=True)
    reports = db.relationship('SafetyReport', backref='community', lazy=True)

    def days_left_in_trial(self):
        if self.plan == 'creator':
            return 999
        if self.is_subscribed:
            return 0
        delta = self.trial_end - datetime.utcnow()
        return max(0, delta.days)

    def is_trial_expired(self):
        if self.plan == 'creator':
            return False
        if self.is_subscribed:
            return False
        return datetime.utcnow() > self.trial_end

    def max_members(self):
        plans = {
            'trial': 50,
            'small': 50,
            'medium': 200,
            'large': 999999,
            'creator': 999999
        }
        return plans.get(self.plan, 50)

    def plan_name(self):
        names = {
            'trial': '🎁 Essai gratuit',
            'small': '🏘️ Petit Quartier',
            'medium': '🏙️ Quartier / Cité',
            'large': '🌆 Grand Quartier',
            'creator': '👑 Créateur'
        }
        return names.get(self.plan, 'Inconnu')

    def plan_price(self):
        prices = {
            'trial': 0,
            'small': 3500,
            'medium': 8000,
            'large': 18000,
            'creator': 0
        }
        return prices.get(self.plan, 0)


class SafetyReport(db.Model):
    __tablename__ = 'safety_reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(20), default='minor')
    category = db.Column(db.String(50), default='suspicious')
    status = db.Column(db.String(20), default='pending')
    urgent_status = db.Column(db.String(20), default='active')
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    address = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'))
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[user_id], backref='reports_created')
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='reports_verified')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id])


class Contribution(db.Model):
    __tablename__ = 'contributions'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'))
    type = db.Column(db.String(20), default='contribution')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id])


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'))
    type = db.Column(db.String(50), default='info')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Fund(db.Model):
    __tablename__ = 'funds'
    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'), unique=True)
    total = db.Column(db.Float, default=0)
    objective = db.Column(db.Float, default=100000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PartnerCode(db.Model):
    __tablename__ = 'partner_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    name = db.Column(db.String(100))
    is_used = db.Column(db.Boolean, default=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)
    sub_code_quota = db.Column(db.Integer, default=5)
    sub_code_used = db.Column(db.Integer, default=0)
    
    used_by = db.relationship('User', foreign_keys=[used_by_id])


class SubCode(db.Model):
    __tablename__ = 'sub_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_email = db.Column(db.String(120))
    recipient_name = db.Column(db.String(100))
    plan_type = db.Column(db.String(20), default='small')
    is_approved = db.Column(db.Boolean, default=False)
    is_used = db.Column(db.Boolean, default=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime)
    
    partner = db.relationship('User', foreign_keys=[partner_id])
    used_by = db.relationship('User', foreign_keys=[used_by_id])


class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50))
    email = db.Column(db.String(120))
    code_attempted = db.Column(db.String(50))
    success = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(50), nullable=False)
    contact_type = db.Column(db.String(20), default='call')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id])


class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'), nullable=False)
    rated_community_id = db.Column(db.Integer, db.ForeignKey('communities.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    month = db.Column(db.String(7))
    status = db.Column(db.String(20), default='pending')
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    validated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    community = db.relationship('Community', foreign_keys=[community_id])
    rated_community = db.relationship('Community', foreign_keys=[rated_community_id])
    validator = db.relationship('User', foreign_keys=[validated_by])


class MonthlyRating(db.Model):
    __tablename__ = 'monthly_ratings'
    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey('communities.id'), nullable=False)
    month = db.Column(db.String(7), nullable=False)
    average_score = db.Column(db.Float, default=0)
    total_votes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    community = db.relationship('Community', foreign_keys=[community_id])