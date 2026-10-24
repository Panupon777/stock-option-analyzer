import asyncio, httpx
from datetime import datetime
from types import SimpleNamespace
from main import app
from auth import get_current_user
from database import SessionLocal, get_db, User, UserRole, Subscription, FlashSale
from config import settings
import scanner

async def main():
    connection=SessionLocal().bind.connect()
    transaction=connection.begin()
    from sqlalchemy.orm import Session
    session=Session(bind=connection, join_transaction_mode='create_savepoint')
    user=User(email='feature-check@example.com',password_hash='not-used',name='Feature QA',role=UserRole.free)
    session.add(user);session.commit()
    def database_override():yield session
    app.dependency_overrides[get_db]=database_override
    app.dependency_overrides[get_current_user]=lambda:user
    original=scanner.finnhub_client.fetch_all_data
    async def fake(ticker):return {'quote':{'current_price':20.0,'change_pct':3.0},'profile':{'name':ticker},'news':[],'sentiment':None,'recommendations':None,'upcoming_earnings':None}
    scanner.finnhub_client.fetch_all_data=fake
    try:
      async with httpx.AsyncClient(app=app,base_url='http://test') as c:
        r=await c.get('/api/scanner/categories');assert r.status_code==200 and any(x['locked'] for x in r.json())
        r=await c.post('/api/scanner/scan',json={'category':'ai_chip'});assert r.status_code==403
        r=await c.post('/api/scanner/scan',json={'category':'popular'});assert r.status_code==200 and len(r.json()['results'])==10
        r=await c.get('/api/glossary');assert r.status_code==200 and len(r.json())==2
        r=await c.post('/api/subscribe/request',json={'slip_note':'QA only'});assert r.status_code==200
        r=await c.get('/api/subscribe/status');assert r.status_code==200 and r.json()['subscription']['status']=='pending' and r.json()['promptpay']
        r=await c.get('/api/admin/subscriptions',headers={'x-admin-password':'wrong'});assert r.status_code==403
        headers={'x-admin-password':settings.admin_password}
        r=await c.get('/api/admin/subscriptions',headers=headers);assert r.status_code==200
        sub=next(s for s in r.json() if s['user_id']==user.id)
        r=await c.post('/api/admin/approve/'+str(sub['id']),headers=headers);assert r.status_code==200
        assert user.role==UserRole.pro
        r=await c.get('/api/scanner/categories');assert r.status_code==200 and not any(x['locked'] for x in r.json())
        r=await c.post('/api/admin/flashsale',headers=headers,json={'price':299,'discount_pct':20,'label':'QA','duration_minutes':5});assert r.status_code==200
        r=await c.get('/api/flashsale');assert r.status_code==200 and r.json()['sale_price']==239
        r=await c.delete('/api/admin/flashsale',headers=headers);assert r.status_code==200
        r=await c.get('/api/history');assert r.status_code==200 and r.json()==[]
        print('PASS: Free/Pro gating, scanner results with missing sentiment, subscription request/status/approval, admin authorization, flash sale lifecycle, glossary, history')
    finally:
      scanner.finnhub_client.fetch_all_data=original
      app.dependency_overrides.clear();session.close();transaction.rollback();connection.close()
      print('All QA database mutations rolled back')
asyncio.run(main())
