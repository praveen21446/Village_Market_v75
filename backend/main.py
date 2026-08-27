from pathlib import Path
from collections import defaultdict,deque
from threading import Lock
import time
import asyncio,base64,hashlib,hmac,httpx,json,os,secrets,shutil,smtplib
from email.message import EmailMessage
from datetime import datetime,timedelta
from fastapi import Depends,FastAPI,File,Form,HTTPException,Request,UploadFile,WebSocket,WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .auth import admin_credentials,create_verified_session,current_user,require_role,send_otp,verify_otp
from .database import SessionLocal,get_db
from .models import AdminAccount,Booking,Crop,Notification,OtpCode,Review,SavedAddress,Session as UserSession,SupportMessage,SupportTicket,User
from .schemas import AddressSave,AdminCreate,AdminLogin,Approval,BookingCreate,CartCheckout,CropRemoval,Decision,NotificationMark,ReviewCreate,SendOtp,StatusUpdate,StockUpdate,VerifyOtp,DeliveryOtpVerify,SupportMessageCreate,SupportStatusUpdate,SupportTicketCreate,AdminCropEdit,AdminUserEdit,Msg91Login
ROOT=Path(__file__).resolve().parents[1];UPLOADS=ROOT/'uploads';UPLOADS.mkdir(exist_ok=True);FRONTEND=ROOT/'frontend'
app=FastAPI(title='Village Market API',version='2.0')

# Lightweight per-instance throttling. For multi-instance/high-scale deployment,
# replace with a shared Redis-backed limiter.
_RATE_BUCKETS=defaultdict(deque)
_RATE_LOCK=Lock()
def _rate_limit(key,limit,window_seconds):
    now=time.monotonic()
    with _RATE_LOCK:
        q=_RATE_BUCKETS[key]
        while q and now-q[0]>=window_seconds:q.popleft()
        if len(q)>=limit:
            retry=max(1,int(window_seconds-(now-q[0])))
            raise HTTPException(429,f'Too many attempts. Try again in {retry} seconds.',headers={'Retry-After':str(retry)})
        q.append(now)

@app.on_event('startup')
def validate_production_security():
    if os.getenv('APP_ENV','development').lower()!='production':
        return
    required=['DATABASE_URL','ADMIN_ID','ADMIN_PASSWORD','MSG91_AUTH_KEY','MSG91_WIDGET_ID','MSG91_WIDGET_TOKEN']
    if os.getenv('STORAGE_BACKEND','local').lower() in {'r2','s3'}:
        required += ['S3_BUCKET','S3_ENDPOINT_URL','S3_ACCESS_KEY_ID','S3_SECRET_ACCESS_KEY','S3_PUBLIC_BASE_URL']
    missing=[k for k in required if not os.getenv(k,'').strip()]
    if missing:
        raise RuntimeError('Missing required production environment variables: '+', '.join(missing))
    admin_pw=os.getenv('ADMIN_PASSWORD','')
    if len(admin_pw)<12 or admin_pw.startswith('CHANGE_ME') or admin_pw=='dev-only-change-me':
        raise RuntimeError('ADMIN_PASSWORD must be a strong production password of at least 12 characters')
    if os.getenv('DATABASE_URL','').lower().startswith('sqlite'):
        raise RuntimeError('Production must use PostgreSQL, not SQLite')

@app.middleware('http')
async def security_and_cache_headers(request,call_next):
    if os.getenv('APP_ENV','development').lower()=='production':
        proto=(request.headers.get('x-forwarded-proto') or request.url.scheme or '').split(',')[0].strip().lower()
        if proto=='http':
            host=request.headers.get('host','')
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f'https://{host}{request.url.path}' + (f'?{request.url.query}' if request.url.query else ''),status_code=308)
    response=await call_next(request)
    # Baseline browser hardening. These headers do not expose application secrets.
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=(self)'
    response.headers['Content-Security-Policy']=(
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' "
        "https://*.msg91.com "
        "https://pass.hostnetsoft.com "
        "https://checkout.razorpay.com; "
        "connect-src 'self' https: wss:; "
        "frame-src "
        "https://*.msg91.com "
        "https://api.razorpay.com "
        "https://checkout.razorpay.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )
    if os.getenv('APP_ENV','development').lower()=='production':
        response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    if request.url.path=='/' or request.url.path.startswith('/static/'):
        response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']='no-cache'
        response.headers['Expires']='0'
    return response
app.mount('/static',StaticFiles(directory=FRONTEND),name='static');app.mount('/uploads',StaticFiles(directory=UPLOADS),name='uploads')
class Manager:
    def __init__(self): self.clients=set();self.loop=None
    async def connect(self,w):
        await w.accept();self.clients.add(w);self.loop=asyncio.get_running_loop()
    def disconnect(self,w): self.clients.discard(w)
    async def broadcast(self,d):
        for w in list(self.clients):
            try: await w.send_json(d)
            except Exception: self.disconnect(w)
manager=Manager()
def external(user,title,message):
    if not user:return
    try:
        if user.email and os.getenv('SMTP_HOST'):
            msg=EmailMessage();msg['Subject']=title;msg['From']=os.getenv('SMTP_FROM',os.getenv('SMTP_USER','no-reply@villagemarket'));msg['To']=user.email;msg.set_content(message)
            with smtplib.SMTP(os.getenv('SMTP_HOST'),int(os.getenv('SMTP_PORT','587')),timeout=10) as s:
                if os.getenv('SMTP_TLS','1')!='0': s.starttls()
                if os.getenv('SMTP_USER'): s.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD',''))
                s.send_message(msg)
    except Exception: pass
    try:
        if user.phone and os.getenv('TWILIO_ACCOUNT_SID') and os.getenv('TWILIO_AUTH_TOKEN') and os.getenv('TWILIO_FROM'):
            from urllib.parse import urlencode
            auth=base64.b64encode(f"{os.getenv('TWILIO_ACCOUNT_SID')}:{os.getenv('TWILIO_AUTH_TOKEN')}".encode()).decode();url=f"https://api.twilio.com/2010-04-01/Accounts/{os.getenv('TWILIO_ACCOUNT_SID')}/Messages.json";httpx.post(url,headers={'Authorization':f'Basic {auth}'},data=urlencode({'From':os.getenv('TWILIO_FROM'),'To':'+91'+user.phone,'Body':f'{title}: {message}'}),timeout=10)
    except Exception: pass
def notify(db,uid,title,msg): db.add(Notification(user_id=uid,title=title,message=msg));external(db.get(User,uid),title,msg)
def notify_admins(db,title,msg):
    for a in db.query(User).filter(User.role=='superadmin').all(): notify(db,a.id,title,msg)
def emit(payload):
    try:
        if manager.loop and manager.loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload),manager.loop)
            return
        loop=asyncio.get_running_loop()
        loop.create_task(manager.broadcast(payload))
    except Exception: pass
def upload(file,uid):
    if not file or not file.filename:return None
    allowed_types={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}
    declared=(file.content_type or '').lower()
    suffix=Path(file.filename).suffix.lower()
    if declared not in allowed_types or suffix not in {'.jpg','.jpeg','.png','.webp'}:
        raise HTTPException(400,'Only JPG, PNG or WEBP crop images are allowed')
    # No application-side image size ceiling. The hosting/storage provider may still enforce its own request/object limits.
    ext=allowed_types[declared]
    fn=f'{uid}_{secrets.token_hex(12)}{ext}'
    backend=os.getenv('STORAGE_BACKEND','local').lower()
    if backend in {'s3','r2'} and os.getenv('S3_BUCKET'):
        try:
            import boto3
            bucket=os.getenv('S3_BUCKET','').strip()
            endpoint=(os.getenv('S3_ENDPOINT_URL') or '').strip().rstrip('/')
            # Cloudflare sometimes shows a bucket-specific S3 URL. boto3 needs the account-level endpoint.
            if endpoint and bucket and endpoint.endswith('/'+bucket):
                endpoint=endpoint[:-(len(bucket)+1)]
            access_key=(os.getenv('S3_ACCESS_KEY_ID') or os.getenv('AWS_ACCESS_KEY_ID') or '').strip()
            secret_key=(os.getenv('S3_SECRET_ACCESS_KEY') or os.getenv('AWS_SECRET_ACCESS_KEY') or '').strip()
            region=(os.getenv('S3_REGION') or os.getenv('AWS_REGION') or 'auto').strip()
            client_kwargs={'region_name':region}
            if endpoint: client_kwargs['endpoint_url']=endpoint
            if access_key: client_kwargs['aws_access_key_id']=access_key
            if secret_key: client_kwargs['aws_secret_access_key']=secret_key
            s3=boto3.client('s3',**client_kwargs)
            key=f'crop-images/{uid}/{fn}'
            s3.upload_fileobj(file.file,bucket,key,ExtraArgs={
                'ContentType':declared,
                'CacheControl':'public, max-age=31536000, immutable',
                'ContentDisposition':'inline',
            })
            base=(os.getenv('S3_PUBLIC_BASE_URL') or '').strip().rstrip('/')
            if not base:
                raise RuntimeError('S3_PUBLIC_BASE_URL is required for buyer-visible crop photos')
            return f'{base}/{key}'
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500,f'Cloud storage upload failed: {e}')
    with open(UPLOADS/fn,'wb') as out: shutil.copyfileobj(file.file,out)
    return f'/uploads/{fn}'
def crop_photos(c):
    photos=[]
    try:
        photos=json.loads(c.photos_json or '[]')
        if not isinstance(photos,list): photos=[]
    except Exception:
        photos=[]
    photos=[str(x) for x in photos if x]
    if c.photo and c.photo not in photos: photos.insert(0,c.photo)
    return photos


def delete_crop_photo_object(photo_url):
    """Best-effort deletion of one crop image from configured storage.

    Cloud deletion failures are intentionally ignored so an admin can still
    remove a crop even when the remote object was already deleted/missing.
    """
    if not photo_url:
        return
    backend=os.getenv('STORAGE_BACKEND','local').lower()
    if backend in {'s3','r2'} and os.getenv('S3_BUCKET'):
        try:
            from urllib.parse import urlparse, unquote
            import boto3
            bucket=os.getenv('S3_BUCKET','').strip()
            base=(os.getenv('S3_PUBLIC_BASE_URL') or '').strip().rstrip('/')
            url=str(photo_url).strip()
            if base and url.startswith(base + '/'):
                key=url[len(base)+1:]
            else:
                parsed=urlparse(url)
                key=unquote(parsed.path.lstrip('/'))
            if not key:
                return
            endpoint=(os.getenv('S3_ENDPOINT_URL') or '').strip().rstrip('/')
            if endpoint and bucket and endpoint.endswith('/'+bucket):
                endpoint=endpoint[:-(len(bucket)+1)]
            access_key=(os.getenv('S3_ACCESS_KEY_ID') or os.getenv('AWS_ACCESS_KEY_ID') or '').strip()
            secret_key=(os.getenv('S3_SECRET_ACCESS_KEY') or os.getenv('AWS_SECRET_ACCESS_KEY') or '').strip()
            region=(os.getenv('S3_REGION') or os.getenv('AWS_REGION') or 'auto').strip()
            client_kwargs={'region_name':region}
            if endpoint: client_kwargs['endpoint_url']=endpoint
            if access_key: client_kwargs['aws_access_key_id']=access_key
            if secret_key: client_kwargs['aws_secret_access_key']=secret_key
            s3=boto3.client('s3',**client_kwargs)
            s3.delete_object(Bucket=bucket,Key=key)
            return
        except Exception:
            return

    # Local-development compatibility.
    try:
        url=str(photo_url)
        if url.startswith('/uploads/'):
            candidate=(UPLOADS/Path(url).name).resolve()
            if candidate.parent==UPLOADS.resolve() and candidate.exists():
                candidate.unlink()
    except Exception:
        pass

def delete_crop_photos(crop):
    for photo_url in set(crop_photos(crop)):
        delete_crop_photo_object(photo_url)
    crop.photo=None
    crop.photos_json='[]'

def crop_private(c,db):
    f=db.get(User,c.farmer_id);photos=crop_photos(c);return {'id':c.id,'name':c.name,'category':c.category,'quantity_kg':c.quantity_kg,'available_kg':c.available_kg,'location':c.location,'address_line':c.address_line,'village':c.village,'mandal':c.mandal,'district':c.district,'state':c.state,'pincode':c.pincode,'landmark':c.landmark,'latitude':c.latitude,'longitude':c.longitude,'expected_price':c.expected_price,'quality':c.quality,'harvest_date':c.harvest_date,'details':c.details,'photo':photos[0] if photos else None,'photos':photos,'status':c.status,'market_price':c.market_price,'admin_note':c.admin_note,'farmer_id':c.farmer_id,'farmer_name':f.name if f else 'Farmer','farmer_phone':f.phone if f else ''}
def crop_public(c,db):
    d=crop_private(c,db)
    for k in ['location','address_line','village','mandal','district','state','pincode','landmark','latitude','longitude','expected_price','admin_note','farmer_id','farmer_name','farmer_phone']:d.pop(k,None)
    return d
def booking_dict(b,db,private=False,expose_otp=False):
    c=db.get(Crop,b.crop_id);buyer=db.get(User,b.buyer_id);farmer=db.get(User,c.farmer_id) if c else None;rv=db.query(Review).filter(Review.booking_id==b.id).first()
    d={'id':b.id,'crop_id':b.crop_id,'crop_name':c.name if c else 'Crop','crop_photo':c.photo if c else None,'harvest_date':c.harvest_date if c else None,'quantity_kg':b.quantity_kg,'amount':b.amount,'final_price':b.final_price,'farmer_note':b.farmer_note,'status':b.status,'payment_status':b.payment_status,'delivery_method':'delivery','delivery_address':b.delivery_address,'created_at':b.created_at.isoformat() if b.created_at else None,'updated_at':b.updated_at.isoformat() if b.updated_at else None,'payment_reference':b.payment_reference,'delivered_at':b.delivered_at.isoformat() if b.delivered_at else None,'review':({'rating':rv.rating,'comment':rv.comment} if rv else None),'has_delivery_otp':bool(b.delivery_otp)}
    if expose_otp and b.status=='shipped': d['delivery_otp']=b.delivery_otp
    if private:d.update({'buyer_name':buyer.name if buyer else 'Buyer','buyer_phone':buyer.phone if buyer else '','farmer_name':farmer.name if farmer else 'Farmer','farmer_phone':farmer.phone if farmer else '','crop_location':c.location if c else '','delivery_latitude':b.delivery_latitude,'delivery_longitude':b.delivery_longitude})
    return d


def support_ticket_dict(ticket,db,include_messages=True):
    owner=db.get(User,ticket.user_id)
    data={'id':ticket.id,'user_id':ticket.user_id,'user_name':owner.name if owner else 'User','user_phone':owner.phone if owner else '','user_role':({'customer':'buyer','vendor':'farmer'}.get(owner.role,owner.role) if owner else ''),'subject':ticket.subject,'category':ticket.category,'status':ticket.status,'created_at':ticket.created_at.isoformat() if ticket.created_at else None,'updated_at':ticket.updated_at.isoformat() if ticket.updated_at else None}
    if include_messages:
        rows=db.query(SupportMessage).filter(SupportMessage.ticket_id==ticket.id).order_by(SupportMessage.id.asc()).all()
        data['messages']=[{'id':m.id,'sender_user_id':m.sender_user_id,'sender_role':m.sender_role,'message':m.message,'created_at':m.created_at.isoformat() if m.created_at else None} for m in rows]
    return data

def st(s):return {'requested':'Order confirmed','farmer_pending_admin':'Farmer accepted · Awaiting admin confirmation','farmer_accepted':'Order accepted','farmer_rejected':'Rejected by farmer','confirmed':'Track your order','processing':'Track your order','shipped':'Shipped','delivered':'Delivered'}.get(s,s.replace('_',' ').title())
def low_stock_check(db,c):
    if c.status=='approved' and c.available_kg<10:
        notify(db,c.farmer_id,'Low stock alert',f'{c.name} has only {c.available_kg:g} kg left. Add stock to reach at least 10 kg. Until then it is automatically hidden from the buyer marketplace.')

def address_dict(a):
    try:data=json.loads(a.data_json or '{}')
    except Exception:data={}
    return {'id':a.id,'kind':a.kind,'label':a.label,'data':data,'created_at':a.created_at.isoformat() if a.created_at else None}
@app.get('/',include_in_schema=False)
def home():return FileResponse(FRONTEND/'index.html')
@app.get('/admin',include_in_schema=False)
def admin_home():return FileResponse(FRONTEND/'admin.html')
@app.get('/privacy',include_in_schema=False)
def privacy_page():return FileResponse(FRONTEND/'privacy.html')
@app.get('/terms',include_in_schema=False)
def terms_page():return FileResponse(FRONTEND/'terms.html')
def _public_msg91_config():
    return {
        'widget_id': os.getenv('MSG91_WIDGET_ID','').strip(),
        'client_token': os.getenv('MSG91_WIDGET_TOKEN','').strip(),
        'configured': bool(os.getenv('MSG91_WIDGET_ID','').strip() and os.getenv('MSG91_WIDGET_TOKEN','').strip()),
    }

def _digits(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())

def _msg91_identifiers(obj):
    """Collect phone-like identifiers from a nested MSG91 response."""
    found=set()
    phone_keys={'identifier','mobile','phone','phone_number','phonenumber','number','user','username'}
    def walk(value,key=''):
        if isinstance(value,dict):
            for k,v in value.items(): walk(v,str(k).lower().replace('-','_'))
        elif isinstance(value,list):
            for v in value: walk(v,key)
        elif key.replace('_','') in {x.replace('_','') for x in phone_keys}:
            d=_digits(value)
            if len(d)>=10: found.add(d)
    walk(obj)
    return found

def _jwt_payload(token):
    try:
        parts=token.split('.')
        if len(parts)<2:return {}
        raw=parts[1]+'='*(-len(parts[1])%4)
        return json.loads(base64.urlsafe_b64decode(raw.encode()).decode())
    except Exception:return {}

async def _verify_msg91_token(access_token,phone):
    authkey=os.getenv('MSG91_AUTH_KEY','').strip()
    if not authkey: raise HTTPException(503,'Real OTP is not configured on the server')
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r=await client.post('https://control.msg91.com/api/v5/widget/verifyAccessToken',json={'authkey':authkey,'access-token':access_token},headers={'Content-Type':'application/json'})
        try: data=r.json()
        except Exception: data={}
    except httpx.RequestError:
        raise HTTPException(502,'Could not contact OTP verification service')
    if r.status_code!=200:
        raise HTTPException(401,'OTP verification failed')
    marker=' '.join(str(data.get(k,'')) for k in ('type','status','message')).lower() if isinstance(data,dict) else ''
    if any(x in marker for x in ('fail','invalid','error','unauthor')):
        raise HTTPException(401,'Invalid or expired OTP verification')
    # MSG91 can represent the same verified Indian number as 10 digits,
    # 91XXXXXXXXXX, +91XXXXXXXXXX, or inside different nested response fields.
    # Bind the verified token to the login phone using the canonical last 10 digits.
    expected10=_digits(phone)[-10:]
    def contains_verified_phone(obj):
        if isinstance(obj,dict):
            return any(contains_verified_phone(v) for v in obj.values())
        if isinstance(obj,list):
            return any(contains_verified_phone(v) for v in obj)
        d=_digits(obj)
        return len(d)>=10 and d[-10:]==expected10
    payload=_jwt_payload(access_token)
    if not (contains_verified_phone(data) or contains_verified_phone(payload)):
        raise HTTPException(401,'Verified mobile number does not match the login number')
    return data

@app.get('/api/auth/msg91-config')
def msg91_config():
    return _public_msg91_config()

@app.post('/api/auth/msg91-login')
async def msg91_login(data:Msg91Login,request:Request,db:Session=Depends(get_db)):
    client_ip=request.client.host if request.client else 'unknown'
    _rate_limit(f'msg91:{client_ip}:{_digits(data.phone)[-10:]}',8,60)
    await _verify_msg91_token(data.access_token,data.phone)
    tok,u=create_verified_session(data.phone,data.role,data.name,data.email,db)
    active=getattr(u,'active_role',u.role)
    return {'token':tok,'user':{'id':u.id,'name':u.name,'phone':u.phone,'email':u.email,'role':active}}

@app.post('/api/auth/send-otp')
def sendotp(data:SendOtp,db:Session=Depends(get_db)):
    if os.getenv('APP_ENV','development').lower()=='production':
        raise HTTPException(410,'Demo OTP is disabled. Use MSG91 real OTP.')
    return {'message':'OTP generated','demo_otp':send_otp(data.phone,db)}
@app.post('/api/auth/verify-otp')
def verifyotp(data:VerifyOtp,db:Session=Depends(get_db)):
    if os.getenv('APP_ENV','development').lower()=='production':
        raise HTTPException(410,'Demo OTP is disabled. Use MSG91 real OTP.')
    tok,u=verify_otp(data.phone,data.code,data.role,data.name,data.email,db);active=getattr(u,'active_role',u.role);return {'token':tok,'user':{'id':u.id,'name':u.name,'phone':u.phone,'email':u.email,'role':active}}
def _hash_admin_password(password:str)->str:
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600000)
    return f'pbkdf2_sha256$600000${salt.hex()}${digest.hex()}'

def _verify_admin_password(password:str,stored:str)->bool:
    try:
        algo,rounds,salt_hex,digest_hex=stored.split('$',3)
        if algo!='pbkdf2_sha256': return False
        check=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt_hex),int(rounds)).hex()
        return hmac.compare_digest(check,digest_hex)
    except Exception:
        return False

@app.post('/api/admin/login')
def admin_login(data:AdminLogin,request:Request,db:Session=Depends(get_db)):
    aid=data.admin_id.strip()
    client_ip=request.client.host if request.client else 'unknown'
    _rate_limit(f'admin-login:{client_ip}:{aid.lower()}',5,300)
    primary_id,primary_pw=admin_credentials()
    account=None
    if hmac.compare_digest(aid,primary_id) and hmac.compare_digest(data.password,primary_pw):
        phone=f'__admin__:{primary_id}'
        u=db.query(User).filter(User.phone==phone).first()
        if not u:
            legacy=db.query(User).filter(User.phone=='__admin__').first()
            if legacy:
                legacy.phone=phone;u=legacy
            else:
                u=User(phone=phone,name='Primary Admin',role='superadmin',verified=True);db.add(u);db.flush()
        u.role='superadmin'
    else:
        account=db.query(AdminAccount).filter(AdminAccount.admin_id==aid,AdminAccount.active==True).first()
        if not account or not _verify_admin_password(data.password,account.password_hash):raise HTTPException(401,'Invalid admin ID or password')
        u=db.get(User,account.user_id)
        if not u:raise HTTPException(401,'Admin account is unavailable')
        u.role='superadmin'
    token=secrets.token_hex(24);db.add(__import__('backend.models',fromlist=['Session']).Session(token=token,user_id=u.id,expires_at=datetime.utcnow()+timedelta(days=1)));db.commit();return {'token':token,'user':{'id':u.id,'name':u.name,'role':u.role,'admin_id':aid}}

@app.get('/api/admin/admins')
def list_admins(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    primary_id,_=admin_credentials()
    rows=[{'id':0,'admin_id':primary_id,'name':'Primary Admin','primary':True,'active':True,'user_id':None}]
    rows.extend({'id':a.id,'admin_id':a.admin_id,'name':a.display_name,'primary':False,'active':a.active,'user_id':a.user_id,'created_at':a.created_at.isoformat() if a.created_at else None} for a in db.query(AdminAccount).order_by(AdminAccount.id.desc()).all())
    return rows

@app.post('/api/admin/admins')
def create_admin(data:AdminCreate,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    admin_id=data.admin_id.strip();name=data.name.strip();primary_id,_=admin_credentials()
    if admin_id.lower()==primary_id.lower() or db.query(AdminAccount).filter(AdminAccount.admin_id==admin_id).first():raise HTTPException(409,'Admin ID already exists')
    phone=f'__admin__:{admin_id}'
    if db.query(User).filter(User.phone==phone).first():raise HTTPException(409,'Admin ID already exists')
    u=User(phone=phone,name=name,role='superadmin',verified=True);db.add(u);db.flush()
    a=AdminAccount(admin_id=admin_id,display_name=name,password_hash=_hash_admin_password(data.password),user_id=u.id,created_by_user_id=admin.id,active=True);db.add(a);db.commit();db.refresh(a)
    return {'id':a.id,'admin_id':a.admin_id,'name':a.display_name,'primary':False,'active':True}

@app.delete('/api/admin/admins/{admin_account_id}')
def delete_admin(admin_account_id:int,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    a=db.get(AdminAccount,admin_account_id)
    if not a:raise HTTPException(404,'Admin account not found')
    if a.user_id==admin.id:raise HTTPException(400,'You cannot remove the admin account you are currently using')
    u=db.get(User,a.user_id)
    db.query(__import__('backend.models',fromlist=['Session']).Session).filter(__import__('backend.models',fromlist=['Session']).Session.user_id==a.user_id).delete()
    db.delete(a)
    if u:db.delete(u)
    db.commit();return {'ok':True}
@app.get('/api/me')
def me(user:User=Depends(current_user)):
    active=getattr(user,'active_role',user.role)
    return {'id':user.id,'name':user.name,'email':user.email,'phone':user.phone,'role':active,'display_role':{'customer':'buyer','vendor':'farmer','superadmin':'admin'}.get(active,active)}
@app.get('/api/addresses')
def saved_addresses(kind:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if kind not in {'delivery','farm'}: raise HTTPException(400,'Invalid address type')
    return [address_dict(a) for a in db.query(SavedAddress).filter(SavedAddress.user_id==user.id,SavedAddress.kind==kind).order_by(SavedAddress.id.desc()).all()]
@app.post('/api/addresses')
def save_address(data:AddressSave,db:Session=Depends(get_db),user:User=Depends(current_user)):
    raw=json.dumps(data.data,ensure_ascii=False,sort_keys=True)
    old=db.query(SavedAddress).filter(SavedAddress.user_id==user.id,SavedAddress.kind==data.kind,SavedAddress.data_json==raw).first()
    if old:return address_dict(old)
    a=SavedAddress(user_id=user.id,kind=data.kind,label=(data.label or 'Saved address').strip()[:100],data_json=raw);db.add(a);db.commit();db.refresh(a);return address_dict(a)
@app.delete('/api/addresses/{address_id}')
def delete_address(address_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    a=db.get(SavedAddress,address_id)
    if not a or a.user_id!=user.id:raise HTTPException(404,'Saved address not found')
    db.delete(a);db.commit();return {'ok':True}
@app.get('/api/categories')
def cats(db:Session=Depends(get_db)):return sorted({c.category for c in db.query(Crop).filter(Crop.status=='approved').all()})
@app.get('/api/crops')
def crops(q:str='',category:str='all',min_price:float|None=None,max_price:float|None=None,sort:str='newest',db:Session=Depends(get_db)):
    rows=db.query(Crop).filter(Crop.status=='approved',Crop.available_kg>=10,Crop.market_price>0).all()
    if q:rows=[c for c in rows if q.lower() in f'{c.name} {c.category} {c.quality}'.lower()]
    if category!='all':rows=[c for c in rows if c.category.lower()==category.lower()]
    if min_price is not None:rows=[c for c in rows if c.market_price>=min_price]
    if max_price is not None:rows=[c for c in rows if c.market_price<=max_price]
    rows.sort(key=(lambda c:c.market_price or 0) if sort=='price_asc' else (lambda c:c.market_price or 0) if sort=='price_desc' else (lambda c:c.available_kg) if sort=='stock_desc' else (lambda c:c.id),reverse=sort in ['price_desc','stock_desc'] if sort!='newest' else True)
    return [crop_public(c,db) for c in rows]
@app.get('/api/crops/{crop_id}')
def crop_detail(crop_id:int,db:Session=Depends(get_db)):
    c=db.get(Crop,crop_id)
    if not c or c.status!='approved' or c.available_kg<10 or not c.market_price or c.market_price<=0:raise HTTPException(404,'Crop not found')
    return crop_public(c,db)
@app.post('/api/crops')
def add_crop(name:str=Form(...),category:str=Form(...),quantity_kg:float=Form(...),location:str=Form(...),address_line:str=Form(''),village:str=Form(''),mandal:str=Form(''),district:str=Form(''),state:str=Form(''),pincode:str=Form(''),landmark:str=Form(''),latitude:str=Form(''),longitude:str=Form(''),expected_price:float=Form(...),quality:str=Form(...),harvest_date:str=Form(...),details:str=Form(''),photos:list[UploadFile]|None=File(None),photo:UploadFile|None=File(None),db:Session=Depends(get_db),farmer:User=Depends(require_role('vendor'))):
    required_text={'name':name,'category':category,'quality':quality,'harvest_date':harvest_date}
    missing=[label for label,value in required_text.items() if not str(value).strip()]
    if missing:raise HTTPException(400,f"Required crop fields missing: {', '.join(missing)}")
    if quantity_kg<10 or expected_price<=0:raise HTTPException(400,'Quantity must be at least 10 kg and price must be positive')
    files=[f for f in (photos or []) if f and f.filename]
    if photo and photo.filename: files.insert(0,photo)
    if not files:raise HTTPException(400,'At least 1 crop photo is required')
    max_photos=max(1,int(os.getenv('MAX_CROP_PHOTOS','8')))
    if len(files)>max_photos:raise HTTPException(400,f'You can upload a maximum of {max_photos} crop photos')
    uploaded=[upload(f,farmer.id) for f in files]
    c=Crop(farmer_id=farmer.id,name=name,category=category,quantity_kg=quantity_kg,available_kg=quantity_kg,location=location,address_line=address_line,village=village,mandal=mandal,district=district,state=state,pincode=pincode,landmark=landmark,latitude=latitude,longitude=longitude,expected_price=expected_price,quality=quality,harvest_date=harvest_date,details=details,photo=uploaded[0],photos_json=json.dumps(uploaded));db.add(c);db.flush();notify_admins(db,'New crop submitted',f'Crop {c.name} is waiting for inspection.');db.commit();emit({'type':'crop_submitted','crop_id':c.id});return crop_private(c,db)
@app.get('/api/farmer/crops')
def fcrops(db:Session=Depends(get_db),farmer:User=Depends(require_role('vendor'))):return [crop_private(c,db) for c in db.query(Crop).filter(Crop.farmer_id==farmer.id).order_by(Crop.id.desc()).all()]
@app.patch('/api/farmer/crops/{crop_id}/stock')
def add_stock(crop_id:int,data:StockUpdate,db:Session=Depends(get_db),farmer:User=Depends(require_role('vendor'))):
    c=db.get(Crop,crop_id)
    if not c or c.farmer_id!=farmer.id:raise HTTPException(404,'Crop not found')
    if c.status!='approved':raise HTTPException(400,'Stock can be added only to an approved crop')
    c.quantity_kg=round(c.quantity_kg+data.quantity_kg,2);c.available_kg=round(c.available_kg+data.quantity_kg,2)
    db.commit();emit({'type':'crop_stock_updated','crop_id':c.id,'available_kg':c.available_kg});return crop_private(c,db)
@app.get('/api/farmer/dashboard')
def fdash(db:Session=Depends(get_db),farmer:User=Depends(require_role('vendor'))):
    crops=db.query(Crop).filter(Crop.farmer_id==farmer.id).all();ids=[c.id for c in crops];orders=db.query(Booking).filter(Booking.crop_id.in_(ids)).all() if ids else [];accepted_statuses={'farmer_pending_admin','farmer_accepted','processing','confirmed','shipped','delivered'};return {'crops':len(crops),'orders':len(orders),'accepted_orders':sum(b.status in accepted_statuses for b in orders),'revenue':sum(b.amount for b in orders if b.status in accepted_statuses),'low_stock':[{'id':c.id,'name':c.name,'available_kg':c.available_kg} for c in crops if c.status=='approved' and c.available_kg<10]}
@app.post('/api/bookings')
def book(data:BookingCreate,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    c=db.get(Crop,data.crop_id)
    if not c or c.status!='approved' or not c.market_price:raise HTTPException(404,'Approved crop with confirmed price not found')
    if c.farmer_id==buyer.id:raise HTTPException(400,'You cannot order your own crop')
    if not (data.delivery_address or '').strip():raise HTTPException(400,'Delivery address is required')
    if data.quantity_kg>c.available_kg:raise HTTPException(400,'Requested quantity exceeds available stock')
    b=Booking(crop_id=c.id,buyer_id=buyer.id,quantity_kg=data.quantity_kg,amount=round(data.quantity_kg*c.market_price,2),final_price=c.market_price,status='requested',delivery_method='delivery',delivery_address=data.delivery_address,delivery_latitude=data.delivery_latitude,delivery_longitude=data.delivery_longitude);c.available_kg=round(c.available_kg-data.quantity_kg,2);db.add(b);db.flush();low_stock_check(db,c);notify(db,c.farmer_id,'New order received',f'You got {data.quantity_kg:g} kg order for {c.name}. Open Bookings to accept or reject.');notify_admins(db,'New buyer order',f'Order #{b.id} placed for {data.quantity_kg:g} kg of {c.name}.');db.commit();emit({'type':'new_order','booking_id':b.id});return {'id':b.id,'status':b.status,'amount':b.amount}
@app.post('/api/bookings/cart')
def cart_checkout(data:CartCheckout,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    if not data.items: raise HTTPException(400,'Cart is empty')
    if not (data.delivery_address or '').strip(): raise HTTPException(400,'Delivery address is required')
    merged={}
    for it in data.items: merged[it.crop_id]=merged.get(it.crop_id,0)+it.quantity_kg
    ids=[];total=0
    for crop_id,qty in merged.items():
        c=db.get(Crop,crop_id)
        if not c or c.status!='approved' or not c.market_price: raise HTTPException(400,'A cart item is no longer available')
        if c.farmer_id==buyer.id: raise HTTPException(400,f'You cannot order your own crop: {c.name}')
        if qty<10: raise HTTPException(400,'Each cart item must be at least 10 kg')
        if qty>c.available_kg: raise HTTPException(400,f'Not enough stock for {c.name}')
        b=Booking(crop_id=c.id,buyer_id=buyer.id,quantity_kg=qty,amount=round(qty*c.market_price,2),final_price=c.market_price,status='requested',delivery_method='delivery',delivery_address=data.delivery_address,delivery_latitude=data.delivery_latitude,delivery_longitude=data.delivery_longitude)
        c.available_kg=round(c.available_kg-qty,2);db.add(b);db.flush();low_stock_check(db,c);ids.append(b.id);total+=b.amount;notify(db,c.farmer_id,'New order received',f'You got {qty:g} kg order for {c.name}. Open Bookings to accept or reject.')
    notify_admins(db,'New cart orders',f'{len(ids)} new buyer orders were placed.');db.commit();emit({'type':'new_orders','booking_ids':ids});return {'booking_ids':ids,'total':round(total,2)}
@app.get('/api/bookings')
def mybookings(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.query(Booking).order_by(Booking.id.desc()).all()
    if user.role=='customer':rows=[b for b in rows if b.buyer_id==user.id]
    elif user.role=='vendor':rows=[b for b in rows if (db.get(Crop,b.crop_id) and db.get(Crop,b.crop_id).farmer_id==user.id)]
    out=[booking_dict(b,db,private=user.role!='customer',expose_otp=user.role=='customer') for b in rows]
    return out
@app.patch('/api/bookings/{booking_id}/decision')
def decision(booking_id:int,data:Decision,db:Session=Depends(get_db),farmer:User=Depends(require_role('vendor'))):
    b=db.get(Booking,booking_id);c=db.get(Crop,b.crop_id) if b else None
    if not b or not c or c.farmer_id!=farmer.id:raise HTTPException(404,'Booking not found')
    if b.status!='requested':raise HTTPException(400,'This order is no longer waiting for farmer response')
    if data.action=='reject':
        r=(data.reason or '').strip()
        if not r:raise HTTPException(400,'Please provide a reason for rejecting the order')
        c.available_kg=round(c.available_kg+b.quantity_kg,2);b.status='farmer_rejected';b.farmer_note=r
    else:b.status='farmer_pending_admin';b.farmer_note='Order accepted by farmer; waiting for admin confirmation.'
    if data.action=='accept':
        notify_admins(db,'Farmer accepted order',f'Order #{b.id} was accepted by the farmer. Please confirm the order for the buyer.')
    else:
        notify(db,b.buyer_id,'Order update',f'{c.name} order ({b.quantity_kg:g} kg) was rejected by the farmer.')
        notify_admins(db,'Order response',f'Order #{b.id}: {b.status}.')
    db.commit();emit({'type':'order_decision','booking_id':b.id,'status':b.status});return booking_dict(b,db,True)
@app.patch('/api/bookings/{booking_id}/cancel')
def cancel_booking(booking_id:int,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    b=db.get(Booking,booking_id);c=db.get(Crop,b.crop_id) if b else None
    if not b or not c or b.buyer_id!=buyer.id: raise HTTPException(404,'Order not found')
    if b.status not in {'requested','farmer_pending_admin'}: raise HTTPException(400,'This order cannot be cancelled now')
    c.available_kg=round(c.available_kg+b.quantity_kg,2)
    b.status='buyer_cancelled'
    b.farmer_note='Order cancelled by buyer.'
    notify(db,c.farmer_id,'Order cancelled',f'Order #{b.id} for {b.quantity_kg:g} kg was cancelled by the buyer.')
    notify_admins(db,'Order cancelled',f'Order #{b.id} was cancelled by the buyer.')
    db.commit();emit({'type':'order_cancelled','booking_id':b.id});return booking_dict(b,db,private=False)

@app.post('/api/bookings/{booking_id}/payment-intent')
def payment_intent(booking_id:int,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    b=db.get(Booking,booking_id)
    if not b or b.buyer_id!=buyer.id:raise HTTPException(404,'Booking not found')
    if b.status!='farmer_accepted':raise HTTPException(400,'Waiting for farmer to accept this order')
    kid=os.getenv('RAZORPAY_KEY_ID');secret=os.getenv('RAZORPAY_KEY_SECRET')
    if kid and secret:
        r=httpx.post('https://api.razorpay.com/v1/orders',auth=(kid,secret),json={'amount':int(b.amount*100),'currency':'INR','receipt':f'vm-{b.id}'},timeout=15)
        if r.status_code>=400:raise HTTPException(502,'Razorpay order creation failed')
        x=r.json();b.payment_reference=x['id'];db.commit();return {'gateway':'razorpay','key_id':kid,'order_id':x['id'],'amount':int(b.amount*100),'currency':'INR'}
    return {'gateway':'not_configured','message':'Configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET for live payments.','amount':b.amount}
@app.post('/api/payments/razorpay/verify')
def verify_payment(payload:dict,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    b=db.get(Booking,int(payload.get('booking_id',0)));secret=os.getenv('RAZORPAY_KEY_SECRET')
    if not b or b.buyer_id!=buyer.id or not secret:raise HTTPException(400,'Invalid payment')
    raw=f"{payload.get('razorpay_order_id')}|{payload.get('razorpay_payment_id')}";sig=hmac.new(secret.encode(),raw.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig,str(payload.get('razorpay_signature'))):raise HTTPException(400,'Payment signature verification failed')
    b.payment_status='paid';b.status='processing';b.payment_reference=payload.get('razorpay_payment_id');notify_admins(db,'Payment received',f'Payment received for order #{b.id}.');db.commit();return {'payment_status':'paid','status':'processing'}
@app.post('/api/bookings/{booking_id}/pay')
def local_pay(booking_id:int,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    raise HTTPException(410,'Demo/local payment has been disabled. Configure Razorpay for live online payments.')
@app.post('/api/bookings/{booking_id}/review')
def add_review(booking_id:int,data:ReviewCreate,db:Session=Depends(get_db),buyer:User=Depends(require_role('customer'))):
    b=db.get(Booking,booking_id)
    if not b or b.buyer_id!=buyer.id:raise HTTPException(404,'Order not found')
    if b.status!='delivered':raise HTTPException(400,'You can review an order after it is delivered')
    if db.query(Review).filter(Review.booking_id==b.id).first():raise HTTPException(400,'Review already submitted')
    db.add(Review(booking_id=b.id,buyer_id=buyer.id,crop_id=b.crop_id,rating=data.rating,comment=data.comment.strip()[:1000]));db.commit();return {'message':'Review submitted'}
@app.get('/api/crops/{crop_id}/reviews')
def reviews(crop_id:int,db:Session=Depends(get_db)):return [{'rating':r.rating,'comment':r.comment,'created_at':r.created_at.isoformat()} for r in db.query(Review).filter(Review.crop_id==crop_id).order_by(Review.id.desc()).all()]
@app.get('/api/notifications')
def notifications(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [{'id':n.id,'title':n.title,'message':n.message,'read':n.read,'created_at':n.created_at.isoformat()} for n in db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.id.desc()).limit(30).all()]
@app.patch('/api/notifications/{notification_id}')
def mark_notification(notification_id:int,data:NotificationMark,db:Session=Depends(get_db),user:User=Depends(current_user)):
    n=db.query(Notification).filter(Notification.id==notification_id,Notification.user_id==user.id).first()
    if not n:raise HTTPException(404,'Notification not found')
    n.read=data.read;db.commit();return {'message':'Updated'}
@app.delete('/api/notifications/{notification_id}')
def dismiss_notification(notification_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    n=db.query(Notification).filter(Notification.id==notification_id,Notification.user_id==user.id).first()
    if not n:raise HTTPException(404,'Notification not found')
    db.delete(n);db.commit();return {'message':'Notification dismissed'}

@app.get('/api/support/tickets')
def support_tickets(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.query(SupportTicket).filter(SupportTicket.user_id==user.id).order_by(SupportTicket.updated_at.desc(),SupportTicket.id.desc()).all()
    return [support_ticket_dict(x,db,True) for x in rows]

@app.post('/api/support/tickets')
def create_support_ticket(data:SupportTicketCreate,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ticket=SupportTicket(user_id=user.id,subject=data.subject.strip(),category=data.category,status='open')
    db.add(ticket);db.flush()
    db.add(SupportMessage(ticket_id=ticket.id,sender_user_id=user.id,sender_role=({'customer':'buyer','vendor':'farmer'}.get(getattr(user,'active_role',user.role),getattr(user,'active_role',user.role))),message=data.message.strip()))
    notify_admins(db,'New live support request',f'{user.name} opened support ticket #{ticket.id}: {ticket.subject}')
    db.commit();db.refresh(ticket);emit({'type':'support_update','ticket_id':ticket.id})
    return support_ticket_dict(ticket,db,True)

@app.post('/api/support/tickets/{ticket_id}/messages')
def user_support_message(ticket_id:int,data:SupportMessageCreate,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ticket=db.query(SupportTicket).filter(SupportTicket.id==ticket_id,SupportTicket.user_id==user.id).first()
    if not ticket: raise HTTPException(404,'Support ticket not found')
    if ticket.status=='closed': raise HTTPException(400,'This support ticket is closed')
    db.add(SupportMessage(ticket_id=ticket.id,sender_user_id=user.id,sender_role=({'customer':'buyer','vendor':'farmer'}.get(getattr(user,'active_role',user.role),getattr(user,'active_role',user.role))),message=data.message.strip()))
    ticket.updated_at=datetime.utcnow();notify_admins(db,'Live support message',f'New message on support ticket #{ticket.id}.')
    db.commit();emit({'type':'support_update','ticket_id':ticket.id})
    return support_ticket_dict(ticket,db,True)

@app.patch('/api/support/tickets/{ticket_id}/status')
def user_support_status(ticket_id:int,data:SupportStatusUpdate,db:Session=Depends(get_db),user:User=Depends(current_user)):
    ticket=db.query(SupportTicket).filter(SupportTicket.id==ticket_id,SupportTicket.user_id==user.id).first()
    if not ticket: raise HTTPException(404,'Support ticket not found')
    ticket.status=data.status;ticket.updated_at=datetime.utcnow();db.commit();emit({'type':'support_update','ticket_id':ticket.id})
    return support_ticket_dict(ticket,db,True)

@app.get('/api/admin/support/tickets')
def admin_support_tickets(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    rows=db.query(SupportTicket).order_by(SupportTicket.status.desc(),SupportTicket.updated_at.desc(),SupportTicket.id.desc()).all()
    return [support_ticket_dict(x,db,True) for x in rows]

@app.post('/api/admin/support/tickets/{ticket_id}/messages')
def admin_support_message(ticket_id:int,data:SupportMessageCreate,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    ticket=db.get(SupportTicket,ticket_id)
    if not ticket: raise HTTPException(404,'Support ticket not found')
    if ticket.status=='closed': raise HTTPException(400,'This support ticket is closed. Reopen it before replying.')
    db.add(SupportMessage(ticket_id=ticket.id,sender_user_id=admin.id,sender_role='admin',message=data.message.strip()))
    ticket.updated_at=datetime.utcnow();notify(db,ticket.user_id,'Live support reply',f'Admin replied to support ticket #{ticket.id}: {ticket.subject}')
    db.commit();emit({'type':'support_update','ticket_id':ticket.id})
    return support_ticket_dict(ticket,db,True)

@app.patch('/api/admin/support/tickets/{ticket_id}/status')
def admin_support_status(ticket_id:int,data:SupportStatusUpdate,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    ticket=db.get(SupportTicket,ticket_id)
    if not ticket: raise HTTPException(404,'Support ticket not found')
    ticket.status=data.status;ticket.updated_at=datetime.utcnow()
    notify(db,ticket.user_id,'Support ticket updated',f'Support ticket #{ticket.id} is now {ticket.status}.')
    db.commit();emit({'type':'support_update','ticket_id':ticket.id})
    return support_ticket_dict(ticket,db,True)

@app.get('/api/admin/pending')
def admin_pending(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):return [crop_private(c,db) for c in db.query(Crop).filter(Crop.status=='pending').order_by(Crop.id.desc()).all()]
@app.patch('/api/admin/crops/{crop_id}')
def admin_crop(crop_id:int,data:Approval,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    c=db.get(Crop,crop_id)
    if not c:raise HTTPException(404,'Crop not found')
    if data.action=='reject':c.status='rejected';c.market_price=None;c.admin_note=data.admin_note or 'Crop rejected by admin.';notify(db,c.farmer_id,'Crop rejected',f'{c.name} was rejected by admin.');db.commit();return crop_private(c,db)
    q=data.inspected_quantity if data.inspected_quantity is not None else c.quantity_kg
    if q<10 or q>c.quantity_kg:raise HTTPException(400,'Verified quantity must be at least 10 kg and cannot exceed submitted quantity')
    if not data.market_price or data.market_price<=0:raise HTTPException(400,'Final price is required')
    c.quantity_kg=round(q,2);c.available_kg=round(q,2);c.quality=(data.inspected_quality or c.quality).strip();c.market_price=round(data.market_price,2);c.status='approved';c.admin_note=data.admin_note or '';notify(db,c.farmer_id,'Crop approved',f'{c.name} approved at ₹{c.market_price:g}/kg.');db.commit();emit({'type':'crop_approved','crop_id':c.id});return crop_private(c,db)
@app.patch('/api/admin/crops/{crop_id}/edit')
def edit_published_crop(crop_id:int,data:AdminCropEdit,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    c=db.get(Crop,crop_id)
    if not c: raise HTTPException(404,'Crop not found')
    if c.status!='approved': raise HTTPException(400,'Only a published crop can be edited here')
    c.name=data.name.strip();c.category=data.category.strip();c.quality=data.quality.strip();c.harvest_date=data.harvest_date.strip();c.details=data.details.strip()
    c.available_kg=round(data.available_kg,2);c.quantity_kg=max(c.quantity_kg,c.available_kg);c.market_price=round(data.market_price,2)
    c.admin_note=data.admin_note.strip() or f'Market details updated by admin on {datetime.utcnow().date().isoformat()}.'
    notify(db,c.farmer_id,'Crop details updated',f'{c.name} marketplace details were updated by admin. Current price: ₹{c.market_price:g}/kg.')
    db.commit();emit({'type':'crop_updated','crop_id':c.id,'market_price':c.market_price});return crop_private(c,db)
@app.get('/api/admin/crops/published')
def published_crops(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    return [crop_private(c,db) for c in db.query(Crop).filter(Crop.status=='approved').order_by(Crop.id.desc()).all()]
@app.patch('/api/admin/crops/{crop_id}/remove')
def remove_market_crop_page(crop_id:int,data:CropRemoval,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    c=db.get(Crop,crop_id)
    if not c:raise HTTPException(404,'Crop not found')
    if c.status!='approved':raise HTTPException(400,'Only a published crop can be removed from the marketplace')
    reason=data.reason.strip()
    delete_crop_photos(c)
    c.status='removed';c.admin_note=f'Removed from marketplace by admin. Reason: {reason}'
    notify(db,c.farmer_id,'Crop removed from marketplace',f'{c.name} was removed from the buyer marketplace by admin. Its stored crop photos were also deleted. Reason: {reason}')
    db.commit();emit({'type':'crop_removed','crop_id':c.id});return crop_private(c,db)
@app.delete('/api/admin/crops/{crop_id}')
def remove_market_crop(crop_id:int,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    c=db.get(Crop,crop_id)
    if not c:raise HTTPException(404,'Crop not found')
    if c.status!='approved':raise HTTPException(400,'Only a published crop can be removed from the marketplace')
    delete_crop_photos(c)
    c.status='removed';c.admin_note='Removed from marketplace by admin.'
    notify(db,c.farmer_id,'Crop removed from marketplace',f'{c.name} was removed from the buyer marketplace by admin. Its stored crop photos were also deleted.')
    db.commit();emit({'type':'crop_removed','crop_id':c.id});return {'ok':True}
@app.get('/api/admin/bookings')
def admin_bookings(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):return [booking_dict(b,db,True) for b in db.query(Booking).order_by(Booking.id.desc()).all()]
@app.patch('/api/admin/bookings/{booking_id}/status')
def admin_status(booking_id:int,data:StatusUpdate,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    b=db.get(Booking,booking_id);c=db.get(Crop,b.crop_id) if b else None
    if not b or not c: raise HTTPException(404,'Order not found')
    if data.status=='admin_cancelled':
        if b.status in {'delivered','admin_cancelled','buyer_cancelled','farmer_rejected'}: raise HTTPException(400,'This order can no longer be cancelled')
        c.available_kg=round(c.available_kg+b.quantity_kg,2);b.status='admin_cancelled';b.farmer_note=(data.reason or 'Order cancelled by admin.').strip()[:500]
        notify(db,b.buyer_id,'Order cancelled',f'Order #{b.id} was cancelled by admin. {b.farmer_note}')
        notify(db,c.farmer_id,'Order cancelled',f'Order #{b.id} was cancelled by admin. {b.farmer_note}')
    elif data.status=='farmer_accepted':
        if b.status!='farmer_pending_admin': raise HTTPException(400,'Farmer must accept the order before admin confirmation')
        b.status='farmer_accepted';b.farmer_note='Farmer and admin confirmed the order.'
        notify(db,b.buyer_id,'Order accepted',f'Order #{b.id} is accepted. Our admin team will contact you.')
    else:
        if data.status=='delivered':
            raise HTTPException(400,'Delivery can only be completed after verifying the buyer delivery OTP')
        allowed={'processing':['farmer_accepted','confirmed'],'shipped':['processing']}
        if b.status not in allowed.get(data.status,[]): raise HTTPException(400,'Invalid order transition')
        b.status=data.status
        if data.status=='shipped':
            b.delivery_otp=f'{secrets.randbelow(1000000):06d}'
            notify(db,b.buyer_id,'Delivery OTP',f'Your order #{b.id} is out for delivery. Delivery OTP: {b.delivery_otp}. Share this OTP with admin only after you receive the order.')
        else:
            notify(db,b.buyer_id,'Order status updated',f'Order #{b.id} is now {data.status.replace("_"," ").title()}.')
    db.commit();emit({'type':'admin_order_update','booking_id':b.id,'status':b.status});return booking_dict(b,db,True)
@app.post('/api/admin/bookings/{bid}/verify-delivery-otp')
def admin_verify_delivery_otp(bid:int,data:DeliveryOtpVerify,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    b=db.get(Booking,bid)
    if not b: raise HTTPException(404,'Order not found')
    if b.status!='shipped': raise HTTPException(400,'Order must be shipped before delivery OTP verification')
    if not b.delivery_otp or not hmac.compare_digest(str(b.delivery_otp),str(data.otp)):
        raise HTTPException(400,'Invalid delivery OTP')
    b.status='delivered';b.delivered_at=datetime.utcnow();b.delivery_otp=None
    notify(db,b.buyer_id,'Order delivered',f'Order #{b.id} has been delivered successfully.')
    c=db.get(Crop,b.crop_id)
    if c: notify(db,c.farmer_id,'Order delivered',f'Order #{b.id} for {c.name} has been delivered successfully.')
    db.commit();emit({'type':'order_status','booking_id':b.id,'status':'delivered'})
    return {'ok':True,'status':'delivered'}

@app.get('/api/admin/users')
def admin_users(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    rows=db.query(User).filter(User.role!='superadmin').order_by(User.id.desc()).all()
    out=[]
    for u in rows:
        session_roles=sorted({r[0] for r in db.query(UserSession.role).filter(UserSession.user_id==u.id).all() if r[0]})
        out.append({'id':u.id,'name':u.name,'phone':u.phone,'email':u.email,'verified':bool(u.verified),'registered_role':u.role,'login_roles':session_roles,'created_at':u.created_at.isoformat() if u.created_at else None})
    return out

@app.patch('/api/admin/users/{user_id}')
def admin_edit_user(user_id:int,data:AdminUserEdit,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    u=db.get(User,user_id)
    if not u or u.role=='superadmin': raise HTTPException(404,'Buyer/Farmer account not found')
    u.name=data.name.strip();u.email=(data.email or '').strip() or None;u.verified=bool(data.verified)
    db.commit();return {'ok':True,'id':u.id,'name':u.name,'email':u.email,'verified':u.verified}

@app.delete('/api/admin/users/{user_id}')
def admin_delete_user(user_id:int,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    u=db.get(User,user_id)
    if not u or u.role=='superadmin': raise HTTPException(404,'Buyer/Farmer account not found')
    # Remove dependent marketplace records deliberately so admin can fully remove an account.
    crop_ids=[r[0] for r in db.query(Crop.id).filter(Crop.farmer_id==u.id).all()]
    booking_ids={r[0] for r in db.query(Booking.id).filter(Booking.buyer_id==u.id).all()}
    if crop_ids:
        booking_ids.update(r[0] for r in db.query(Booking.id).filter(Booking.crop_id.in_(crop_ids)).all())
    if booking_ids:
        db.query(Review).filter(Review.booking_id.in_(booking_ids)).delete(synchronize_session=False)
        db.query(Booking).filter(Booking.id.in_(booking_ids)).delete(synchronize_session=False)
    if crop_ids:
        db.query(Review).filter(Review.crop_id.in_(crop_ids)).delete(synchronize_session=False)
        db.query(Crop).filter(Crop.id.in_(crop_ids)).delete(synchronize_session=False)
    ticket_ids=[r[0] for r in db.query(SupportTicket.id).filter(SupportTicket.user_id==u.id).all()]
    if ticket_ids:
        db.query(SupportMessage).filter(SupportMessage.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        db.query(SupportTicket).filter(SupportTicket.id.in_(ticket_ids)).delete(synchronize_session=False)
    db.query(SupportMessage).filter(SupportMessage.sender_user_id==u.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id==u.id).delete(synchronize_session=False)
    db.query(SavedAddress).filter(SavedAddress.user_id==u.id).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id==u.id).delete(synchronize_session=False)
    db.query(OtpCode).filter(OtpCode.phone==u.phone).delete(synchronize_session=False)
    db.delete(u);db.commit();emit({'type':'admin_user_deleted','user_id':user_id});return {'ok':True}

@app.delete('/api/admin/bookings/{booking_id}')
def admin_delete_booking(booking_id:int,db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    b=db.get(Booking,booking_id)
    if not b: raise HTTPException(404,'Order not found')
    c=db.get(Crop,b.crop_id)
    if c and b.status not in {'delivered','buyer_cancelled','admin_cancelled','farmer_rejected'}:
        c.available_kg=round(c.available_kg+b.quantity_kg,2)
    db.query(Review).filter(Review.booking_id==booking_id).delete(synchronize_session=False)
    db.delete(b);db.commit();emit({'type':'admin_order_deleted','booking_id':booking_id});return {'ok':True}

@app.get('/api/admin/vendors')
def vendors(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    out=[]
    accepted_statuses={'farmer_pending_admin','farmer_accepted','processing','confirmed','shipped','delivered'}
    farmer_ids=[row[0] for row in db.query(Crop.farmer_id).distinct().all()]
    for v in db.query(User).filter(User.id.in_(farmer_ids)).all() if farmer_ids else []:
        crops=db.query(Crop).filter(Crop.farmer_id==v.id).all();ids=[c.id for c in crops];all_orders=db.query(Booking).filter(Booking.crop_id.in_(ids)).all() if ids else [];orders=[x for x in all_orders if x.status in accepted_statuses]
        out.append({'id':v.id,'name':v.name,'phone':v.phone,'crops':len(crops),'accepted_orders':len(orders),'revenue':sum(x.amount for x in orders)})
    return out
@app.get('/api/admin/analytics')
def analytics(db:Session=Depends(get_db),admin:User=Depends(require_role('superadmin'))):
    paid=db.query(Booking).filter(Booking.payment_status=='paid').all();by={};daily={}
    for b in paid:
        name=db.get(Crop,b.crop_id).name if db.get(Crop,b.crop_id) else 'Unknown';by[name]=by.get(name,0)+b.amount;key=(b.created_at or datetime.utcnow()).strftime('%Y-%m-%d');daily[key]=daily.get(key,0)+b.amount
    low=[{'id':c.id,'name':c.name,'available_kg':c.available_kg} for c in db.query(Crop).filter(Crop.status=='approved').all() if c.available_kg<10]
    return {'total_revenue':sum(x.amount for x in paid),'paid_orders':len(paid),'top_crops':[{'name':k,'revenue':v} for k,v in sorted(by.items(),key=lambda x:x[1],reverse=True)[:8]],'daily_sales':[{'date':k,'revenue':v} for k,v in sorted(daily.items())],'low_stock':low}
@app.websocket('/ws/admin')
async def ws_admin(ws:WebSocket):
    await manager.connect(ws)
    try:
        while True:await ws.receive_text()
    except WebSocketDisconnect:manager.disconnect(ws)
    except Exception:manager.disconnect(ws)
