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
def verify_otp(phone,code,role,name,email,db):
    otp=db.query(OtpCode).filter(OtpCode.phone==phone,OtpCode.code==code).first()
    if not otp or otp.expires_at<datetime.utcnow(): raise HTTPException(400,'Invalid or expired OTP')
    desired=canonical_role(role);user=db.query(User).filter(User.phone==phone,User.role==desired).first()
    clean_name=(name or '').strip()
    if not user:
        if not clean_name: raise HTTPException(400,'Name is required')
        user=User(phone=phone,role=desired,name=clean_name,email=email or None);db.add(user);db.flush()
    else:
        if user.role=='superadmin': raise HTTPException(403,'Admin account cannot be used in the customer app')
        if clean_name: user.name=clean_name
        if email: user.email=email
    token=secrets.token_hex(24);db.add(Session(token=token,user_id=user.id,expires_at=datetime.utcnow()+timedelta(days=7)));db.delete(otp);db.commit();return token,user
def admin_credentials(): return os.getenv('ADMIN_ID','admin'),os.getenv('ADMIN_PASSWORD','looser@123')
def current_user(authorization:str|None=Header(None),db:DbSession=Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Please sign in')
    s=db.get(Session,authorization[7:]);
    if not s or s.expires_at<datetime.utcnow(): raise HTTPException(401,'Session expired')
    u=db.get(User,s.user_id)
    if not u: raise HTTPException(401,'User not found')
    return u
def require_role(role):
    want=canonical_role(role)
    def dep(user:User=Depends(current_user)):
        if user.role!=want: raise HTTPException(403,f'{role.title()} access required')
        return user
    return dep
