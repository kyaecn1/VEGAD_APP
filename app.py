from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Community, SafetyReport, Message, Contribution, Notification, Fund, PartnerCode, SubCode, Contact, Rating, MonthlyRating
from datetime import datetime, timedelta
import random
import string
import re

app = Flask(__name__)
app.secret_key = 'vega-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vega.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print("✅ Base de données prête !")


# ============ CONSTANTES ============
CREATOR_EMAILS = [
    'kya.christopher25@gmail.com',
    'kyaecn1@gmail.com',
]
CREATOR_CODE = 'VEGAD-CREATOR-MASTER-2026'
PARTNER_CODES = ['VEGAD2026', 'VEGAD-PARTENAIRE', 'VEGAD-BETA', 'VEGAD-ADMIN']


# ============ FONCTIONS UTILES ============
def get_current_user():
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])


def get_current_community():
    user = get_current_user()
    if user and user.community_id:
        return Community.query.get(user.community_id)
    return None


def check_trial_status():
    community = get_current_community()
    if not community:
        return None
    
    if community.plan == 'creator':
        return {
            'is_trial': False,
            'is_expired': False,
            'days_left': 999,
            'is_subscribed': True,
            'plan_name': '👑 Créateur',
            'plan_price': 0
        }
    
    return {
        'is_trial': community.plan == 'trial',
        'is_expired': community.is_trial_expired(),
        'days_left': community.days_left_in_trial(),
        'is_subscribed': community.is_subscribed,
        'plan_name': community.plan_name(),
        'plan_price': community.plan_price()
    }


def is_admin(user):
    return user and user.role in ['admin', 'representative', 'creator']


# ============ ACCUEIL ============
@app.route('/')
def accueil():
    communities = Community.query.filter_by(is_active=True).all()
    return render_template('accueil.html', communities=communities)


# ============ AUTHENTIFICATION ============
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            if user.email.lower() in [e.lower() for e in CREATOR_EMAILS]:
                user.role = 'creator'
                db.session.commit()
                flash(f'👑 Bienvenue Créateur {user.username} !', 'success')
            else:
                flash(f'Bienvenue {user.username} !', 'success')
            
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['community_id'] = user.community_id
            
            if not user.community_id:
                return redirect(url_for('choose_community'))
            if user.role in ['admin', 'representative', 'creator']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('feed'))
        flash('Email ou mot de passe incorrect.', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        partner_code = request.form.get('partner_code', '').strip().upper()
        
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('register'))
        
        is_creator = email.lower() in [e.lower() for e in CREATOR_EMAILS]
        
        if not is_creator:
            if len(password) < 8:
                flash('Le mot de passe doit faire au moins 8 caractères.', 'danger')
                return redirect(url_for('register'))
            if not re.search(r'[A-Z]', password):
                flash('Le mot de passe doit contenir au moins 1 majuscule.', 'danger')
                return redirect(url_for('register'))
            if not re.search(r'[0-9]', password):
                flash('Le mot de passe doit contenir au moins 1 chiffre.', 'danger')
                return redirect(url_for('register'))
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                flash('Le mot de passe doit contenir au moins 1 caractère spécial.', 'danger')
                return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return redirect(url_for('register'))
        
        role = 'member'
        
        if email.lower() in [e.lower() for e in CREATOR_EMAILS]:
            role = 'creator'
            flash('👑 Compte Créateur créé ! Connectez-vous.', 'success')
        elif partner_code:
            if partner_code == CREATOR_CODE:
                role = 'creator'
                flash('👑 Code Créateur activé !', 'success')
            elif partner_code in PARTNER_CODES:
                role = 'representative'
                flash('✅ Code partenaire activé !', 'success')
            else:
                flash('⚠️ Code invalide, compte créé comme membre.', 'warning')
        
        u = User(username=username, email=email, password=password, role=role)
        db.session.add(u)
        db.session.commit()
        
        if role == 'member':
            flash(f'Compte créé ! Connectez-vous.', 'success')
        
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Vous êtes déconnecté.', 'success')
    return redirect(url_for('accueil'))


# ============ CHOIX COMMUNAUTÉ ============
@app.route('/choose-community')
def choose_community():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user.community_id:
        if is_admin(user):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('feed'))
    
    search = request.args.get('search', '').strip()
    query = Community.query.filter_by(is_active=True)
    if search:
        query = query.filter(Community.name.ilike(f'%{search}%'))
    communities = query.all()
    
    return render_template('choose_community.html', user=user, communities=communities, search=search)


# ============ PRICING ============
@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/subscribe/<plan>')
def subscribe(plan):
    user = get_current_user()
    if not is_admin(user):
        flash('Seul le représentant peut gérer l\'abonnement.', 'danger')
        return redirect(url_for('feed'))
    community = get_current_community()
    if not community:
        return redirect(url_for('choose_community'))
    if plan not in ['small', 'medium', 'large']:
        flash('Forfait invalide.', 'danger')
        return redirect(url_for('pricing'))
    community.plan = plan
    community.is_subscribed = True
    community.subscription_start = datetime.utcnow()
    community.subscription_end = datetime.utcnow() + timedelta(days=30)
    db.session.commit()
    flash(f'✅ Abonnement "{community.plan_name()}" activé !', 'success')
    return redirect(url_for('admin_dashboard'))


# ============ FEED ============
@app.route('/feed')
def feed():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    community = Community.query.get(user.community_id)
    if community.is_trial_expired():
        flash('⚠️ Essai terminé. Choisissez un forfait.', 'warning')
        return redirect(url_for('pricing'))
    
    urgent = SafetyReport.query.filter_by(
        alert_type='urgent', urgent_status='active',
        community_id=user.community_id
    ).order_by(SafetyReport.created_at.desc()).limit(3).all()
    
    verified = SafetyReport.query.filter_by(
        alert_type='minor', status='approved',
        community_id=user.community_id
    ).order_by(SafetyReport.created_at.desc()).limit(3).all()
    
    recent_messages = Message.query.filter_by(
        community_id=user.community_id
    ).order_by(Message.created_at.desc()).limit(3).all()
    
    notifications = Notification.query.filter_by(
        user_id=user.id
    ).order_by(Notification.created_at.desc()).limit(3).all()
    
    fund_obj = Fund.query.filter_by(community_id=user.community_id).first()
    if not fund_obj:
        fund_obj = Fund(community_id=user.community_id, total=0, objective=100000)
        db.session.add(fund_obj)
        db.session.commit()
    
    fund = {
        'total': int(fund_obj.total),
        'objective': int(fund_obj.objective),
        'percentage': int((fund_obj.total / fund_obj.objective * 100) if fund_obj.objective > 0 else 0)
    }
    
    trial_info = check_trial_status()
    
    return render_template('feed.html', 
                         user=user, 
                         community=community,
                         urgent_alerts=urgent,
                         verified_alerts=verified,
                         recent_messages=recent_messages,
                         notifications=notifications,
                         fund=fund,
                         trial_info=trial_info)


# ============ MESSAGERIE ============
@app.route('/messages', methods=['GET', 'POST'])
def messages():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            msg = Message(
                content=content,
                sender_id=user.id,
                community_id=user.community_id
            )
            db.session.add(msg)
            db.session.commit()
            flash('✅ Message envoyé !', 'success')
        return redirect(url_for('messages'))
    
    community_messages = Message.query.filter_by(
        community_id=user.community_id
    ).order_by(Message.created_at.desc()).all()
    
    return render_template('messages.html', user=user, messages=community_messages)


# ============ CAISSE ============
@app.route('/fund')
def fund():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    
    fund_obj = Fund.query.filter_by(community_id=user.community_id).first()
    if not fund_obj:
        fund_obj = Fund(community_id=user.community_id, total=0, objective=100000)
        db.session.add(fund_obj)
        db.session.commit()
    
    contributions = Contribution.query.filter_by(
        community_id=user.community_id
    ).order_by(Contribution.created_at.desc()).all()
    
    total = sum(c.amount for c in contributions if c.type == 'contribution')
    expenses = sum(c.amount for c in contributions if c.type == 'expense')
    
    return render_template('fund.html', 
                         user=user, 
                         fund=fund_obj,
                         contributions=contributions,
                         total=total,
                         expenses=expenses)


@app.route('/fund/contribute', methods=['GET', 'POST'])
def fund_contribute():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        description = request.form.get('description', '').strip()
        type_contribution = request.form.get('type', 'contribution')
        
        if amount and amount > 0:
            c = Contribution(
                amount=amount,
                description=description,
                user_id=user.id,
                community_id=user.community_id,
                type=type_contribution
            )
            db.session.add(c)
            
            fund_obj = Fund.query.filter_by(community_id=user.community_id).first()
            if fund_obj:
                if type_contribution == 'contribution':
                    fund_obj.total += amount
                else:
                    fund_obj.total -= amount
                db.session.commit()
            
            flash(f'✅ {"Contribution" if type_contribution == "contribution" else "Dépense"} enregistrée !', 'success')
            return redirect(url_for('fund'))
        else:
            flash('Montant invalide.', 'danger')
    
    return render_template('fund_contribute.html', user=user)


# ============ NOTIFICATIONS ============
@app.route('/notifications')
def notifications():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    
    notifs = Notification.query.filter_by(
        user_id=user.id
    ).order_by(Notification.created_at.desc()).all()
    
    return render_template('notifications.html', user=user, notifications=notifs)


@app.route('/notifications/read/<int:notif_id>')
def notification_read(notif_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    notif = Notification.query.get(notif_id)
    if notif and notif.user_id == user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('notifications'))


# ============ DASHBOARD ADMIN ============
@app.route('/admin')
def admin_dashboard():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not is_admin(user):
        flash('Accès réservé aux admins.', 'danger')
        return redirect(url_for('feed'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    community = Community.query.get(user.community_id)
    if community.is_trial_expired():
        flash('⚠️ Essai terminé.', 'warning')
        return redirect(url_for('pricing'))
    users = User.query.all()
    communities = Community.query.all()
    pending = SafetyReport.query.filter_by(
        alert_type='minor', status='pending'
    ).order_by(SafetyReport.created_at.desc()).all()
    urgent = SafetyReport.query.filter_by(
        alert_type='urgent', urgent_status='active'
    ).order_by(SafetyReport.created_at.desc()).all()
    members = User.query.filter_by(community_id=user.community_id).all()
    trial_info = check_trial_status()
    return render_template('admin.html', user=user, users=users, communities=communities,
                          pending_alerts=pending, urgent_alerts=urgent,
                          community=community, community_members=members, trial_info=trial_info)


# ============ PROMOTION / RÉTROGRADATION ============
@app.route('/admin/promote/<int:user_id>', methods=['POST'])
def promote_user(user_id):
    current = get_current_user()
    if not current or current.role not in ['representative', 'creator']:
        flash('Seul le représentant peut faire ça.', 'danger')
        return redirect(url_for('admin_dashboard'))
    target = User.query.get(user_id)
    if target and target.community_id == current.community_id and target.id != current.id:
        target.role = 'admin'
        db.session.commit()
        flash(f'✅ {target.username} est admin.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/demote/<int:user_id>', methods=['POST'])
def demote_user(user_id):
    current = get_current_user()
    if not current or current.role not in ['representative', 'creator']:
        flash('Seul le représentant peut faire ça.', 'danger')
        return redirect(url_for('admin_dashboard'))
    target = User.query.get(user_id)
    if target and target.community_id == current.community_id and target.id != current.id:
        target.role = 'member'
        db.session.commit()
        flash(f'⚠️ {target.username} est membre.', 'warning')
    return redirect(url_for('admin_dashboard'))


# ============ COMMUNAUTÉS ============
@app.route('/communities')
def communities_list():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    search = request.args.get('search', '').strip()
    city_filter = request.args.get('city', '').strip()
    query = Community.query.filter_by(is_active=True)
    if search:
        query = query.filter(Community.name.ilike(f'%{search}%'))
    if city_filter:
        query = query.filter(Community.city.ilike(f'%{city_filter}%'))
    communities = query.all()
    all_cities = db.session.query(Community.city).filter(
        Community.city.isnot(None), Community.city != ''
    ).distinct().all()
    cities = [c[0] for c in all_cities]
    return render_template('communities.html', communities=communities, cities=cities,
                          search=search, city_filter=city_filter, user=user)


@app.route('/communities/create', methods=['GET', 'POST'])
def community_create():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if user.role == 'admin':
        flash('Un admin ne peut pas créer de communauté.', 'danger')
        return redirect(url_for('admin_dashboard'))
    if user.role == 'member' and user.community_id:
        flash('Vous avez déjà une communauté.', 'warning')
        return redirect(url_for('feed'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        city = request.form.get('city')
        address = request.form.get('address')
        if Community.query.filter_by(name=name).first():
            flash('Ce nom existe déjà.', 'danger')
            return redirect(url_for('community_create'))
        
        if user.role == 'creator':
            new_c = Community(name=name, description=description, city=city, address=address, plan='creator')
        else:
            new_c = Community(name=name, description=description, city=city, address=address, plan='trial')
        
        db.session.add(new_c)
        db.session.commit()
        user.community_id = new_c.id
        
        if user.role != 'creator':
            user.role = 'representative'
        
        db.session.commit()
        session['community_id'] = new_c.id
        session['role'] = user.role
        
        fund_obj = Fund(community_id=new_c.id, total=0, objective=100000)
        db.session.add(fund_obj)
        db.session.commit()
        
        if user.role == 'creator':
            flash(f'👑 Communauté créée ! Forfait Créateur illimité à vie activé.', 'success')
        else:
            flash(f'🎉 Communauté créée ! Essai de 17 jours activé.', 'success')
        
        return redirect(url_for('admin_dashboard'))
    return render_template('community_form.html')


@app.route('/communities/join/<int:community_id>')
def community_join(community_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    community = Community.query.get(community_id)
    if not community:
        flash('Communauté introuvable.', 'danger')
        return redirect(url_for('communities_list'))
    current = User.query.filter_by(community_id=community_id).count()
    if current >= community.max_members():
        flash('Communauté pleine.', 'danger')
        return redirect(url_for('communities_list'))
    user.community_id = community_id
    if user.role not in ['admin', 'representative', 'creator']:
        user.role = 'member'
    db.session.commit()
    session['community_id'] = community_id
    flash(f'Vous avez rejoint "{community.name}" !', 'success')
    if user.role in ['admin', 'representative', 'creator']:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('feed'))


@app.route('/communities/view/<int:community_id>')
def community_view(community_id):
    community = Community.query.get(community_id)
    if not community:
        return redirect(url_for('communities_list'))
    members = User.query.filter_by(community_id=community_id).all()
    return render_template('community_view.html', community=community, members=members)


# ============ ALERTES ============
@app.route('/alerts')
def alerts_list():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    community = Community.query.get(user.community_id)
    if community.is_trial_expired():
        return redirect(url_for('pricing'))
    urgent = SafetyReport.query.filter_by(
        alert_type='urgent', urgent_status='active',
        community_id=user.community_id
    ).order_by(SafetyReport.created_at.desc()).all()
    verified = SafetyReport.query.filter_by(
        alert_type='minor', status='approved',
        community_id=user.community_id
    ).order_by(SafetyReport.created_at.desc()).all()
    pending = []
    if is_admin(user):
        pending = SafetyReport.query.filter_by(
            alert_type='minor', status='pending',
            community_id=user.community_id
        ).order_by(SafetyReport.created_at.desc()).all()
    return render_template('alerts.html', user=user, urgent_alerts=urgent,
                          verified_alerts=verified, pending_alerts=pending)


@app.route('/alerts/create', methods=['GET', 'POST'])
def alert_create():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    community = Community.query.get(user.community_id)
    if community.is_trial_expired():
        return redirect(url_for('pricing'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        alert_type = request.form.get('alert_type', 'minor')
        category = request.form.get('category', 'suspicious')
        address = request.form.get('address')
        status = 'pending' if alert_type == 'minor' else 'approved'
        urgent_status = 'active' if alert_type == 'urgent' else 'inactive'
        a = SafetyReport(title=title, description=description, alert_type=alert_type,
                        category=category, status=status, urgent_status=urgent_status,
                        address=address, user_id=user.id, community_id=user.community_id)
        db.session.add(a)
        db.session.commit()
        
        if alert_type == 'minor':
            admins = User.query.filter(
                User.community_id == user.community_id,
                User.role.in_(['admin', 'representative', 'creator'])
            ).all()
            for admin in admins:
                notif = Notification(
                    title=f'Nouvelle alerte mineure : {title}',
                    content=description[:100],
                    user_id=admin.id,
                    community_id=user.community_id,
                    type='alert_minor'
                )
                db.session.add(notif)
            db.session.commit()
            flash('⚠️ Alerte créée. En attente de validation.', 'info')
        else:
            members = User.query.filter_by(community_id=user.community_id).all()
            for member in members:
                if member.id != user.id:
                    notif = Notification(
                        title=f'🚨 ALERTE URGENTE : {title}',
                        content=description[:100],
                        user_id=member.id,
                        community_id=user.community_id,
                        type='alert_urgent'
                    )
                    db.session.add(notif)
            db.session.commit()
            flash('🚨 Alerte URGENTE publiée !', 'danger')
        
        return redirect(url_for('alerts_list'))
    return render_template('alert_form.html', user=user)


@app.route('/alerts/view/<int:alert_id>')
def alert_view(alert_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    alert = SafetyReport.query.get(alert_id)
    if not alert:
        return redirect(url_for('alerts_list'))
    can_view = (alert.alert_type == 'urgent' or alert.status == 'approved'
                or is_admin(user))
    if not can_view:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('alerts_list'))
    return render_template('alert_view.html', alert=alert, user=user)


@app.route('/alerts/verify/<int:alert_id>', methods=['POST'])
def alert_verify(alert_id):
    user = get_current_user()
    if not is_admin(user):
        return redirect(url_for('feed'))
    alert = SafetyReport.query.get(alert_id)
    if not alert:
        return redirect(url_for('alerts_list'))
    action = request.form.get('action')
    if action == 'approve':
        alert.status = 'approved'
        alert.verified_by = user.id
        alert.verified_at = datetime.utcnow()
        notif = Notification(
            title=f'✅ Votre alerte "{alert.title}" a été validée',
            content='Elle est maintenant visible par toute la communauté.',
            user_id=alert.user_id,
            community_id=alert.community_id,
            type='alert_approved'
        )
        db.session.add(notif)
        flash('✅ Alerte validée !', 'success')
    elif action == 'reject':
        alert.status = 'rejected'
        alert.verified_by = user.id
        alert.verified_at = datetime.utcnow()
        alert.rejection_reason = request.form.get('reason', 'Non spécifiée')
        notif = Notification(
            title=f'❌ Votre alerte "{alert.title}" a été rejetée',
            content=f'Raison : {alert.rejection_reason}',
            user_id=alert.user_id,
            community_id=alert.community_id,
            type='alert_rejected'
        )
        db.session.add(notif)
        flash('❌ Alerte rejetée.', 'warning')
    db.session.commit()
    return redirect(url_for('alerts_list'))


@app.route('/alerts/resolve/<int:alert_id>')
def alert_resolve(alert_id):
    user = get_current_user()
    if not is_admin(user):
        return redirect(url_for('feed'))
    alert = SafetyReport.query.get(alert_id)
    if alert:
        alert.urgent_status = 'resolved'
        db.session.commit()
        flash('✅ Alerte résolue.', 'success')
    return redirect(url_for('alerts_list'))


# ============ CODE PARTENAIRE ============
@app.route('/partner-code', methods=['GET', 'POST'])
def partner_code():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        
        if code == CREATOR_CODE:
            user.role = 'creator'
            db.session.commit()
            session['role'] = 'creator'
            flash('👑 Code Créateur activé ! Vous avez accès total.', 'success')
            return redirect(url_for('admin_dashboard'))
        
        elif code in PARTNER_CODES:
            user.role = 'representative'
            db.session.commit()
            session['role'] = 'representative'
            flash('✅ Code valide ! Vous êtes maintenant Partenaire.', 'success')
            return redirect(url_for('community_create'))
        
        else:
            flash('❌ Code invalide.', 'danger')
            return redirect(url_for('partner_code'))
    
    return render_template('partner_code.html', user=user)


# ============ ADMIN PARTENAIRES ============
@app.route('/admin/partners')
def admin_partners():
    user = get_current_user()
    if not is_admin(user):
        flash('Accès réservé aux admins.', 'danger')
        return redirect(url_for('feed'))
    
    partners = PartnerCode.query.order_by(PartnerCode.created_at.desc()).all()
    sub_codes = SubCode.query.order_by(SubCode.created_at.desc()).all()
    
    return render_template('admin_partner.html', 
                         user=user, 
                         partners=partners, 
                         sub_codes=sub_codes)


@app.route('/admin/partners/create', methods=['POST'])
def admin_partner_create():
    user = get_current_user()
    if not is_admin(user):
        return redirect(url_for('feed'))
    
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    quota = request.form.get('quota', 5, type=int)
    
    if not email:
        flash('Email requis.', 'danger')
        return redirect(url_for('admin_partners'))
    
    code = 'VEGAD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    partner = PartnerCode(
        code=code,
        email=email,
        name=name,
        phone=phone,
        sub_code_quota=quota
    )
    db.session.add(partner)
    db.session.commit()
    
    flash(f'✅ Code partenaire créé : {code} pour {email}', 'success')
    return redirect(url_for('admin_partners'))


@app.route('/admin/partners/delete/<int:partner_id>', methods=['POST'])
def admin_partner_delete(partner_id):
    user = get_current_user()
    if not is_admin(user):
        return redirect(url_for('feed'))
    
    partner = PartnerCode.query.get(partner_id)
    if partner:
        db.session.delete(partner)
        db.session.commit()
        flash('✅ Code partenaire supprimé.', 'success')
    
    return redirect(url_for('admin_partners'))


# ============ AUTORITÉS ============
@app.route('/authorities')
def authorities():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    
    community = Community.query.get(user.community_id)
    if community.plan in ['creator', 'large']:
        contacts = Contact.query.filter_by(user_id=user.id).order_by(Contact.created_at.desc()).all()
    elif community.plan == 'medium':
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        contacts = Contact.query.filter(
            Contact.user_id == user.id,
            Contact.created_at >= three_months_ago
        ).order_by(Contact.created_at.desc()).all()
    else:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        contacts = Contact.query.filter(
            Contact.user_id == user.id,
            Contact.created_at >= thirty_days_ago
        ).order_by(Contact.created_at.desc()).all()
    
    return render_template('authorities.html', user=user, contacts=contacts)


@app.route('/authorities/log', methods=['POST'])
def authorities_log():
    user = get_current_user()
    if not user:
        return {'status': 'error', 'message': 'Non connecté'}, 401
    
    data = request.get_json()
    service = data.get('service', 'Inconnu')
    
    contact = Contact(
        service=service,
        contact_type='call',
        user_id=user.id,
        community_id=user.community_id
    )
    db.session.add(contact)
    db.session.commit()
    
    return {'status': 'ok'}


@app.route('/authorities/services')
def authorities_services():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    return render_template('authorities_services.html', user=user)


# ============ ÉVALUATION ============
@app.route('/rating')
def rating():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    if not user.community_id:
        return redirect(url_for('choose_community'))
    
    community = Community.query.get(user.community_id)
    current_month = datetime.utcnow().strftime('%Y-%m')
    
    # Classement des communautés de la même ville
    city_communities = Community.query.filter_by(
        city=community.city,
        is_active=True
    ).all()
    
    ranked_communities = []
    for c in city_communities:
        ratings = Rating.query.filter_by(
            rated_community_id=c.id,
            status='approved'
        ).all()
        if ratings:
            avg_score = sum(r.score for r in ratings) / len(ratings)
        else:
            avg_score = c.safety_score
        
        ranked_communities.append({
            'community': c,
            'score': round(avg_score, 1)
        })
    
    ranked_communities.sort(key=lambda x: x['score'], reverse=True)
    
    other_communities = Community.query.filter(
        Community.city == community.city,
        Community.id != community.id,
        Community.is_active == True
    ).limit(5).all()
    
    my_ratings = Rating.query.filter_by(
        community_id=community.id,
        month=current_month
    ).all()
    
    already_rated = len(my_ratings) > 0
    can_vote = user.role in ['representative', 'creator', 'admin']
    has_voted_this_month = len(my_ratings) > 0
    
    return render_template('rating.html', 
                         user=user, 
                         community=community,
                         ranked_communities=ranked_communities,
                         other_communities=other_communities,
                         my_ratings=my_ratings,
                         current_month=current_month,
                         already_rated=already_rated,
                         can_vote=can_vote,
                         has_voted_this_month=has_voted_this_month)


@app.route('/rating/submit', methods=['POST'])
def rating_submit():
    user = get_current_user()
    if not user or not user.community_id:
        return redirect(url_for('login'))
    
    rated_community_id = request.form.get('rated_community_id', type=int)
    score = request.form.get('score', type=float)
    comment = request.form.get('comment', '').strip()
    
    if not rated_community_id or not score:
        flash('Données invalides.', 'danger')
        return redirect(url_for('rating'))
    
    community = Community.query.get(user.community_id)
    current_month = datetime.utcnow().strftime('%Y-%m')
    
    existing = Rating.query.filter_by(
        community_id=community.id,
        rated_community_id=rated_community_id,
        month=current_month
    ).first()
    
    if existing:
        flash('Vous avez déjà noté ce quartier ce mois-ci.', 'warning')
        return redirect(url_for('rating'))
    
    r = Rating(
        community_id=community.id,
        rated_community_id=rated_community_id,
        score=score,
        comment=comment,
        month=current_month,
        status='pending'
    )
    db.session.add(r)
    db.session.commit()
    
    flash('✅ Note envoyée ! En attente de validation par VEGAD.', 'success')
    return redirect(url_for('rating'))


@app.route('/rating/start-vote')
def rating_start_vote():
    user = get_current_user()
    if not user or user.role not in ['representative', 'creator']:
        flash('Seul le représentant peut lancer un vote.', 'danger')
        return redirect(url_for('rating'))
    
    flash('📅 Vote mensuel lancé ! Les membres peuvent maintenant noter.', 'success')
    return redirect(url_for('rating'))

# ============ PROFIL ============
@app.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        flash('Connectez-vous d\'abord.', 'danger')
        return redirect(url_for('login'))
    
    community = None
    if user.community_id:
        community = Community.query.get(user.community_id)
    
    messages_count = Message.query.filter_by(sender_id=user.id).count()
    alerts_count = SafetyReport.query.filter_by(user_id=user.id).count()
    contributions_count = Contribution.query.filter_by(user_id=user.id).count()
    
    return render_template('profile.html', 
                         user=user, 
                         community=community,
                         messages_count=messages_count,
                         alerts_count=alerts_count,
                         contributions_count=contributions_count)


@app.route('/profile/edit', methods=['GET', 'POST'])
def profile_edit():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != user.id:
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return redirect(url_for('profile_edit'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user.id:
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('profile_edit'))
        
        user.username = username
        user.email = email
        user.phone = phone
        user.address = address
        
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                allowed = {'png', 'jpg', 'jpeg', 'gif'}
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
                if ext in allowed:
                    import os
                    filename = f"user_{user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
                    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    
                    if user.photo and user.photo != 'default.png':
                        old_path = os.path.join(upload_folder, user.photo)
                        if os.path.exists(old_path):
                            try:
                                os.remove(old_path)
                            except:
                                pass
                    
                    user.photo = filename
                    flash('✅ Photo mise à jour !', 'success')
                else:
                    flash('❌ Format non supporté.', 'danger')
        
        db.session.commit()
        session['username'] = username
        flash('✅ Profil mis à jour !', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile_edit.html', user=user)


@app.route('/profile/change-password', methods=['GET', 'POST'])
def profile_change_password():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current = request.form.get('current_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        
        if user.password != current:
            flash('Mot de passe actuel incorrect.', 'danger')
            return redirect(url_for('profile_change_password'))
        
        if new != confirm:
            flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('profile_change_password'))
        
        if len(new) < 6:
            flash('Le nouveau mot de passe doit faire au moins 6 caractères.', 'danger')
            return redirect(url_for('profile_change_password'))
        
        user.password = new
        db.session.commit()
        flash('✅ Mot de passe changé !', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile_password.html', user=user)

if __name__ == '__main__':
    app.run(debug=False, port=5000)