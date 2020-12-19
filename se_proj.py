from flask import Flask,flash,redirect,render_template,request,session,abort,url_for
import os
import pymysql
import time
import requests
import json

app = Flask(__name__)

@app.route('/')
def home():
	return render_template('login.html')
@app.route('/multi')
def multiauth():
	res = requests.get('http://192.168.43.156:9999')
	j = json.loads(res.text)
	if j['grant']=='Y':
		return render_template('multimodal.html')
	else:
		return render_template('login.html')

@app.route('/search', methods=['POST'])
def do_search():
	noOfBeds = request.form['beds']
	ac = request.form['ac']
	db = pymysql.connect(host='localhost',user='root',passwd='root')
	cur = db.cursor()
	cur.execute('use first_db;')
	cur.execute('select * from room where beds = %d and ac = "%s" and availability=1;'%(int(noOfBeds),ac))
	tup = cur.fetchall()
	cur.close()
	db.commit()
	db.close()
	print(noOfBeds,ac)
	return avail(tup)

@app.route('/avail')
def avail(t):
	return render_template('availability.html',tupl = t)

@app.route('/accept',methods=['POST'])
def accept(status=True,val=0,stat="LENGTH OF USERNAME AND PASSWORD SHOULD BE AT LEAST 8"):
	if status==True:
		roomno = request.form['roomno']
	else:
		roomno=val
	db = pymysql.connect(host='localhost',user='root',passwd='root')
	cur = db.cursor()
	cur.execute('use first_db;')
	cur.execute('select availability from room where room_no=%d;'%(int(roomno)))
	status = cur.fetchone()
	if status[0] == None or status[0] == 0:
		return 'Error Occurred'
	cur.close()
	db.commit()
	db.close()
	return render_template('details.html',roomno = roomno,stat=stat)

@app.route('/signup',methods=['POST'])
def signup():
	username = request.form['username']
	passwd = request.form['password']
	aadhar = request.form['aadhar']
	roomno = request.form['roomno']
	db = pymysql.connect(host='localhost',user='root',passwd='root')
	cur = db.cursor()
	cur.execute('use first_db;')
	cur.execute('select * from cust where username="%s" and passwd="%s";'%(username,passwd))
	res = cur.fetchone()
	if res is not None:
		cur.close()
		db.commit()
		db.close()
		return accept(status=False,val=roomno,stat="USERNAME ALREADY EXISTS")
	if len(username)<8 or len(passwd)<8 :
		cur.close()
		db.commit()
		db.close()
		return accept(status=False,val=roomno)
	if len(aadhar)!=10:
		cur.close()
		db.commit()
		db.close()
		return accept(status=False,val=roomno,stat="INVALID AADHAR NO.")
	cur.execute('select max(custid) from cust;')
	cid = cur.fetchone()
	if cid[0] is None:
		cid = 0
	else:
		cid = cid[0]
	print(type(cid),cid)
	print(type(roomno),roomno)
	print(type(aadhar),aadhar)
	cur.execute('insert into cust values(%d,"%s","%s",%d,%d,%d,0);'%(cid+1,username,passwd,int(roomno),int(aadhar),time.time()))
	cur.execute('update room set availability=0 where room_no=%d'%(int(roomno)))
	cur.execute('update rc set cid=%d where rid=%d'%(cid+1,int(roomno)))
	cur.execute('update room set custid=%d where room_no=%d'%(cid+1,int(roomno)))
	cur.close()
	db.commit()
	db.close()
	return render_template('thanks.html',status="Checking In",desc="Have a great stay !!!")

@app.route('/login',methods=['POST'])
def open_dashboard():
	user = request.form['username']
	passwd = request.form['password']
	print(user,passwd)
	db = pymysql.connect(host='localhost',user='root',passwd='root')
	cur = db.cursor()
	cur.execute('use first_db;')
	cur.execute('select * from cust where username="%s" and passwd="%s";'%(user,passwd))
	res = cur.fetchone()
	if res is None:
		cur.close()
		db.commit()
		db.close()
		return home()
	cur.execute('select * from menu;')
	tup = cur.fetchall()
	cur.close()
	db.commit()
	db.close()
	return render_template('open_dashboard.html',tupl=tup,user=user,passwd=passwd)

@app.route('/placeord',methods=['POST'])
def place():
	itemno = request.form['itemno']
	itemno = int(itemno)
	qty = request.form['qty']
	qty = int(qty)
	uname = request.form['uname']
	passw = request.form['passw']
	db = pymysql.connect(host='localhost',user='root',passwd='root')
	cur = db.cursor()
	cur.execute('use first_db;')
	cur.execute('select price from menu where oid=%d;'%(itemno))
	res = cur.fetchone()
	cur.execute('update cust set bill = bill+%d where username="%s" and passwd="%s";'%(res[0]*qty,uname,passw))
	cur.close()
	db.commit()
	db.close()
	return render_template('thanks.html',status="Placing Order",desc="Order will arive at your room in a while...")

@app.route('/checkout',methods=['POST'])
def checkout():
	feed = request.form['feedback']
	uname = request.form['uname']
	passw = request.form['passw']
	db = pymysql.connect(host='localhost',user='root',passwd='root')
	cur = db.cursor()
	cur.execute('use first_db;')
	cur.execute('select * from cust where username="%s" and passwd="%s";'%(uname,passw))
	res = cur.fetchone()
	cid = res[0]
	bill = res[6]
	rid = res[3]
	aad = res[4]
	checkin = res[5]
	checkout = time.time()
	cur.execute('delete from cust where custid=%d;'%(cid))
	cur.execute('update rc set cid=NULL where rid=%d;'%(rid))
	cur.execute('select price from room where room_no=%d;'%(rid))
	res = cur.fetchone()
	print(type(res[0]),res[0])
	bill = bill+((int(checkout-checkin)//(24*3600))*res[0])
	cur.execute('update room set availability=1,custid=NULL where room_no=%d;'%(rid))
	cur.execute('insert into logtab values(%d,%d,"%s","%s",%d,%d,%d,%d,"%s");'%(cid,rid,uname,passw,aad,checkin,checkout,bill,feed))

	cur.close()
	db.commit()
	db.close()
	return render_template('thanks.html',status="Choosing HotelSA",desc="YOUR BILL IS %d. Please pay at the reception. Hope you had a great stay with us...See you soon..."%(bill))
if __name__=="__main__":
	app.run(host='0.0.0.0',port=5000)

	