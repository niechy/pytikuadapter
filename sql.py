import sqlite3,os
path=os.path.join('.','data')
print(path)
if not os.path.exists(path):
    os.mkdir(path)

if os.path.isfile(path.join("question.db")):
    database = sqlite3.connect(os.path.join(path,"question.db"))

else :
    database = sqlite3.connect(os.path.join(path,"question.db"))
# database = sqlite3.connect("data")# 这里目前硬编码为这个，以后有config再改为能调的吧
# db=database.cursor()
# db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='question'")
# result = db.fetchone()
#
# if result:
#     print("表 'question' 存在")
# else:
#     print("表 'question' 不存在")