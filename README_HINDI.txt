KHALIDAUTODOC.COM — MOTORCYCLE DOCUMENTS WEBSITE STARTER
========================================================

Website ka naam/address preference: Khalidautodoc.com
NOTE: Domain abhi sirf aapki pasand ke roop mein set hai; yeh domain kharida ya website live nahi hui hai.

Is project mein:
- Motorcycle-only document storefront
- Customer signup/login
- Admin panel se bike documents upload karna aur price set karna
- UPI payment link + UTR/transaction reference submit karna
- Admin payment verify karke approve/reject kar sakta hai
- Approve hone ke baad hi customer document download kar sakta hai
- Original files private_documents folder mein rehti hain; public direct links nahi hain

Aap motorcycle documents jaise Bike Service Manual, Wiring Diagram, ECU Diagram,
BS6/BS7 bike technical documents aur engine repair guide rakh sakte hain.

IMPORTANT:
Yeh starter website hai, abhi internet par live nahi hai.
UPI payment automatic verify nahi hota. Admin ko apne UPI app/bank statement mein payment check karke manually approve karna hoga.
UPI QR image abhi add karni hogi. UPI_ID aur PAYEE_NAME ko apni details se set karein.
Public launch se pehle SECRET_KEY, ADMIN_USERNAME aur ADMIN_PASSWORD ko environment variables se change karein.
Sirf wahi documents upload/sell karein jinhe distribute karne ka aapke paas adhikar hai.

LOCAL COMPUTER PAR RUN KARNE KA TARIKA
1. Python 3.10+ install karein.
2. Is folder mein terminal/command prompt kholein.
3. Run: pip install -r requirements.txt
4. Apni UPI details set karein (example):
   Windows PowerShell:
     $env:UPI_ID="yourupi@bank"
     $env:PAYEE_NAME="Khalid AutoDoc"
     $env:ADMIN_USERNAME="admin"
     $env:ADMIN_PASSWORD="ApnaStrongPassword"
     $env:SECRET_KEY="LongRandomSecretKey"
   Mac/Linux:
     export UPI_ID="yourupi@bank"
     export PAYEE_NAME="Khalid AutoDoc"
     export ADMIN_USERNAME="admin"
     export ADMIN_PASSWORD="ApnaStrongPassword"
     export SECRET_KEY="LongRandomSecretKey"
5. Run: python app.py
6. Browser mein http://127.0.0.1:5000 kholein.

Default local admin login (sirf testing ke liye):
Username: admin
Password: ChangeMe123!
PUBLIC WEBSITE PAR IS DEFAULT PASSWORD KE SAATH KABHI DEPLOY NA KAREIN.

LIVE KARNE KE LIYE:
Khalidautodoc.com domain ko domain registrar se kharidna hoga, phir Python/Flask support
wali hosting par deploy karke domain connect karna hoga. Database aur private_documents
folder persistent storage par hon, aur HTTPS enabled ho.
Public deployment se pehle security review, backups, privacy policy, terms, refund policy,
aur applicable tax/legal requirements check karein.
