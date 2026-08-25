from pydantic import BaseModel,Field
class SendOtp(BaseModel): phone:str=Field(pattern=r'^[0-9]{10}$')
class VerifyOtp(BaseModel): phone:str=Field(pattern=r'^[0-9]{10}$');code:str=Field(pattern=r'^[0-9]{6}$');role:str=Field(pattern=r'^(buyer|farmer|customer|vendor)$');name:str=Field(min_length=2,max_length=100);email:str|None=None
class AdminLogin(BaseModel): admin_id:str=Field(min_length=1,max_length=80);password:str=Field(min_length=1,max_length=128)
class AdminCreate(BaseModel): admin_id:str=Field(min_length=3,max_length=80,pattern=r'^[A-Za-z0-9_.@-]+$');name:str=Field(min_length=2,max_length=100);password:str=Field(min_length=8,max_length=128)
class BookingCreate(BaseModel): crop_id:int;quantity_kg:float=Field(ge=10);delivery_method:str=Field(pattern=r'^delivery$');delivery_address:str|None=None;delivery_latitude:str|None=None;delivery_longitude:str|None=None
class CartItem(BaseModel): crop_id:int;quantity_kg:float=Field(ge=10)
class CartCheckout(BaseModel): items:list[CartItem];delivery_address:str|None=None;delivery_latitude:str|None=None;delivery_longitude:str|None=None
class Decision(BaseModel): action:str=Field(pattern=r'^(accept|reject)$');reason:str|None=None
class Approval(BaseModel): action:str=Field(pattern=r'^(approve|reject)$');market_price:float|None=None;inspected_quantity:float|None=Field(default=None,ge=0);inspected_quality:str|None=None;admin_note:str=''
class StatusUpdate(BaseModel): status:str=Field(pattern=r'^(farmer_accepted|processing|shipped|delivered|admin_cancelled)$');reason:str|None=None
class ReviewCreate(BaseModel): rating:int=Field(ge=1,le=5);comment:str=''
class NotificationMark(BaseModel): read:bool=True

class AddressSave(BaseModel): kind:str=Field(pattern=r'^(delivery|farm)$');label:str='Saved address';data:dict
class StockUpdate(BaseModel): quantity_kg:float=Field(gt=0)


class AdminCropEdit(BaseModel):
    name:str|None=Field(default=None,min_length=2,max_length=100)
    category:str|None=Field(default=None,min_length=2,max_length=40)
    quantity_kg:float|None=Field(default=None,ge=10)
    expected_price:float|None=Field(default=None,gt=0)
    market_price:float|None=Field(default=None,gt=0)
    quality:str|None=Field(default=None,min_length=1,max_length=50)
    harvest_date:str|None=Field(default=None,min_length=8,max_length=20)
    details:str|None=Field(default=None,max_length=4000)
    admin_note:str|None=Field(default=None,max_length=1000)

class CropRemoval(BaseModel):
    reason:str=Field(min_length=3,max_length=500)

class DeliveryOtpVerify(BaseModel): otp:str=Field(pattern=r'^[0-9]{6}$')

class SupportTicketCreate(BaseModel):
    subject:str=Field(min_length=3,max_length=120)
    category:str=Field(default='general',pattern=r'^(order|crop|account|payment|delivery|technical|general)$')
    message:str=Field(min_length=2,max_length=2000)

class SupportMessageCreate(BaseModel):
    message:str=Field(min_length=1,max_length=2000)

class SupportStatusUpdate(BaseModel):
    status:str=Field(pattern=r'^(open|closed)$')

