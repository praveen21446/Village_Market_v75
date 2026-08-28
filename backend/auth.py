from datetime import datetime,timedelta
import hashlib,hmac,os,secrets
from fastapi import Depends,Header,HTTPException
from sqlalchemy.orm import Session as DbSession
from .database import get_db
from .models import OtpCode,Session,User
ROLE_MAP={'buyer':'customer','customer':'customer','farmer':'vendor','vendor':'vendor','admin':'superadmin','superadmin':'superadmin'}
def canonical_role(r):
    if r not in ROLE_MAP: raise HTTPException(400,'Unsupported role')
    return ROLE_MAP[r]
def send_otp(phone,db):
    code=f'{secrets.randbelow(1000000):06d}';db.query(OtpCode).filter(OtpCode.phone==phone).delete();db.add(OtpCode(phone=phone,code=code,expires_at=datetime.utcnow()+timedelta(minutes=5)));db.commit();return code
def create_verified_session(phone,role,name,email,db):
    """Create a Village Market session after the phone has been verified externally."""
    desired=canonical_role(role);user=db.query(User).filter(User.phone==phone).first()
    clean_name=(name or '').strip()
    if not user:
        if not clean_name:
            digits=''.join(ch for ch in str(phone) if ch.isdigit())
            clean_name=f'User {digits[-4:]}' if digits else 'Village Market User'
        user=User(phone=phone,role=desired,name=clean_name,email=email or None,verified=True);db.add(user);db.flush()
    else:
        if user.role=='superadmin': raise HTTPException(403,'Admin account cannot be used in the customer app')
        if clean_name: user.name=clean_name
        if email: user.email=email
        user.verified=True
    token=secrets.token_hex(24);db.add(Session(token=token,user_id=user.id,role=desired,expires_at=datetime.utcnow()+timedelta(days=7)));db.commit()
    user.active_role=desired
    return token,user

def verify_otp(phone,code,role,name,email,db):
    """Local/demo OTP verifier. Production login uses MSG91 instead."""
    otp=db.query(OtpCode).filter(OtpCode.phone==phone,OtpCode.code==code).first()
    if not otp or otp.expires_at<datetime.utcnow(): raise HTTPException(400,'Invalid or expired OTP')
    db.delete(otp);db.flush()
    return create_verified_session(phone,role,name,email,db)
def admin_credentials():
    admin_id=os.getenv('ADMIN_ID','').strip()
    admin_password=os.getenv('ADMIN_PASSWORD','')
    if os.getenv('APP_ENV','development').lower()=='production':
        if not admin_id or not admin_password:
            raise HTTPException(503,'Admin credentials are not configured securely on the server')
        return admin_id,admin_password
    return admin_id or 'admin',admin_password or 'dev-only-change-me'
def current_user(authorization:str|None=Header(None),db:DbSession=Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Please sign in')
    s=db.get(Session,authorization[7:]);
    if not s or s.expires_at<datetime.utcnow(): raise HTTPException(401,'Session expired')
    u=db.get(User,s.user_id)
    if not u: raise HTTPException(401,'User not found')
    u.active_role=s.role or u.role
    return u
def require_role(role):
    want=canonical_role(role)
    def dep(user:User=Depends(current_user)):
        if getattr(user,'active_role',user.role)!=want: raise HTTPException(403,f'{role.title()} access required')
        return user
    return dep
