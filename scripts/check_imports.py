import importlib
modules = ['ttkbootstrap','sqlalchemy','pydantic','tkinter']
missing = []
for m in modules:
    try:
        importlib.import_module(m)
    except Exception as e:
        missing.append((m,str(e)))
if missing:
    for m,err in missing:
        print(f'MISSING:{m} => {err}')
else:
    print('ALL_IMPORTS_OK')
