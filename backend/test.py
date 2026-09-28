import traceback
try:
    from app.main import app
    print('Success!')
except Exception as e:
    traceback.print_exc()
